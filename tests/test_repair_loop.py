from __future__ import annotations

import copy
import hashlib
import json
import unittest

from semantic_guard.repair_loop import (
    RepairContractError,
    assess_repair_effect,
    build_independent_repair_review,
    build_repair_cycle,
    build_repair_effect_review_basis,
    build_responsibility_material,
    build_responsibility_policy,
    record_repair_attempt,
    validate_repair_cycle,
    validate_responsibility_material,
    validate_responsibility_policy,
)


def _sha(seed: str) -> dict[str, str]:
    return {"algorithm": "sha256", "value": hashlib.sha256(seed.encode()).hexdigest()}


def _ref(entity_id: str, seed: str | None = None) -> dict[str, object]:
    return {"entity_id": entity_id, "entity_digest": _sha(seed or entity_id)}


def _vref(entity_id: str, version: str, seed: str | None = None) -> dict[str, object]:
    return {
        "entity_id": entity_id,
        "entity_version": version,
        "entity_digest": _sha(seed or entity_id),
    }


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _reseal_policy(policy: dict[str, object]) -> None:
    basis = copy.deepcopy(policy)
    for field in (
        "adoption_state",
        "human_decision_ref",
        "policy_basis_digest",
        "policy_digest",
    ):
        basis.pop(field, None)
    policy["policy_basis_digest"] = {
        "algorithm": "sha256",
        "value": hashlib.sha256(_canonical(basis)).hexdigest(),
    }
    if policy["adoption_state"] == "adopted" and policy["human_decision_ref"] is not None:
        policy["human_decision_ref"]["target_id"] = policy["policy_id"]
        policy["human_decision_ref"]["target_version"] = policy["policy_version"]
        policy["human_decision_ref"]["target_basis_digest"] = copy.deepcopy(
            policy["policy_basis_digest"]
        )
    material = copy.deepcopy(policy)
    material.pop("policy_digest", None)
    policy["policy_digest"] = {
        "algorithm": "sha256",
        "value": hashlib.sha256(_canonical(material)).hexdigest(),
    }


def _reseal_material(material: dict[str, object]) -> None:
    identity = copy.deepcopy(material)
    identity.pop("material_id", None)
    identity.pop("material_digest", None)
    material["material_id"] = "responsibility-material." + hashlib.sha256(
        _canonical(identity)
    ).hexdigest()
    digest_basis = copy.deepcopy(material)
    digest_basis.pop("material_digest", None)
    material["material_digest"] = {
        "algorithm": "sha256",
        "value": hashlib.sha256(_canonical(digest_basis)).hexdigest(),
    }


def _reseal_cycle(cycle: dict[str, object], *, identity: bool = False) -> None:
    if identity:
        basis = {
            "schema_version": cycle["schema_version"],
            "subject_ref": cycle["subject_ref"],
            "before_audit_ref": cycle["before_audit_ref"],
            "findings": cycle["findings"],
        }
        cycle["cycle_id"] = "repair-cycle." + hashlib.sha256(
            _canonical(basis)
        ).hexdigest()
    effect = cycle["effect_assessment"]
    effect_basis = copy.deepcopy(effect)
    effect_basis.pop("effect_basis_digest", None)
    effect_basis.pop("independent_review_refs", None)
    effect["effect_basis_digest"] = {
        "algorithm": "sha256",
        "value": hashlib.sha256(_canonical(effect_basis)).hexdigest(),
    }
    for review in effect["independent_review_refs"]:
        review["target_effect_basis_digest"] = copy.deepcopy(
            effect["effect_basis_digest"]
        )
        review_basis = copy.deepcopy(review)
        review_basis.pop("review_digest", None)
        review["review_digest"] = {
            "algorithm": "sha256",
            "value": hashlib.sha256(_canonical(review_basis)).hexdigest(),
        }
    digest_basis = copy.deepcopy(cycle)
    digest_basis.pop("cycle_digest", None)
    cycle["cycle_digest"] = {
        "algorithm": "sha256",
        "value": hashlib.sha256(_canonical(digest_basis)).hexdigest(),
    }


def _reseal_review(review: dict[str, object]) -> None:
    basis = copy.deepcopy(review)
    basis.pop("review_digest", None)
    review["review_digest"] = {
        "algorithm": "sha256",
        "value": hashlib.sha256(_canonical(basis)).hexdigest(),
    }


class RepairLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        roles = [
            {
                "role_id": "role.coding-agent",
                "actor_class": "coding_agent",
                "decision_rights": [
                    "acquire_evidence",
                    "bounded_technical_interpretation",
                    "propose_repair",
                    "execute_authorized_repair",
                    "run_reaudit",
                ],
                "limitations": ["Cannot change intent, accept risk, grant authority, or accept completion."],
            },
            {
                "role_id": "role.requester",
                "actor_class": "human_requester",
                "decision_rights": [
                    "change_intent_or_scope",
                    "accept_residual_risk",
                    "authorize_external_effect",
                ],
                "limitations": ["Technical claims still require audit evidence."],
            },
            {
                "role_id": "role.approver",
                "actor_class": "human_approver",
                "decision_rights": ["final_acceptance", "grant_or_expand_authority"],
                "limitations": ["Acceptance does not rewrite technical evidence."],
            },
            {
                "role_id": "role.control-plane",
                "actor_class": "external_control_plane",
                "decision_rights": ["schedule_or_delegate"],
                "limitations": ["Does not audit or accept the result."],
            },
        ]
        rules = [
            {
                "issue_class": "implementation_defect",
                "accountable_role_id": "role.coding-agent",
                "permitted_role_ids": ["role.coding-agent"],
                "required_right": "execute_authorized_repair",
                "technical_work_before_escalation": True,
                "escalation_conditions": ["Repair changes declared intent or external authority."],
            },
            {
                "issue_class": "missing_evidence",
                "accountable_role_id": "role.coding-agent",
                "permitted_role_ids": ["role.coding-agent"],
                "required_right": "acquire_evidence",
                "technical_work_before_escalation": True,
                "escalation_conditions": ["Evidence acquisition requires an external effect."],
            },
            {
                "issue_class": "scope_or_intent_choice",
                "accountable_role_id": "role.requester",
                "permitted_role_ids": ["role.requester"],
                "required_right": "change_intent_or_scope",
                "technical_work_before_escalation": False,
                "escalation_conditions": ["More than one materially different intent remains."],
            },
            {
                "issue_class": "final_acceptance",
                "accountable_role_id": "role.approver",
                "permitted_role_ids": ["role.approver"],
                "required_right": "final_acceptance",
                "technical_work_before_escalation": False,
                "escalation_conditions": ["A final acceptance decision is requested."],
            },
        ]
        pending_policy = build_responsibility_policy(
            policy_id="policy.responsibility.example",
            policy_version="1.0.0",
            adoption_state="pending",
            roles=roles,
            issue_rules=rules,
        )
        self.policy = build_responsibility_policy(
            policy_id="policy.responsibility.example",
            policy_version="1.0.0",
            adoption_state="adopted",
            roles=roles,
            issue_rules=rules,
            human_decision_ref={
                "decision_id": "decision.policy-adoption.1",
                "decision_kind": "adopt_responsibility_policy",
                "target_id": pending_policy["policy_id"],
                "target_version": pending_policy["policy_version"],
                "target_basis_digest": copy.deepcopy(
                    pending_policy["policy_basis_digest"]
                ),
                "status": "accepted",
                "decided_by": "human.owner",
                "decision_maker_identity": _vref(
                    "human.owner", "1", "human-owner"
                ),
                "decision_maker_kind": "human",
                "external_to_semantic_guard": True,
                "decided_at": "2026-07-16T01:00:00Z",
                "record_ref": {
                    "record_id": "record.policy-adoption.1",
                    "record_locator": "decisions/responsibility-policy-1.json",
                    "record_digest": _sha("policy-adoption"),
                },
            },
        )
        self.subject = _vref("subject.requirement.1", "r1", "before-subject")
        self.audit_before = _ref("audit.before.1", "audit-before")
        self.target = {
            "target_id": "target.requirement.scenario",
            "target_ref": copy.deepcopy(self.subject),
            "locator": "scenario",
            "defect_hypothesis": "The declared actor is not the action agent.",
            "intended_effect": "Make actor and performed action unambiguous.",
            "success_criteria": ["The relation audit no longer reports the actor-role conflict."],
            "regression_guards": ["guard.result-preserved", "guard.scope-preserved"],
            "prohibited_shortcuts": [
                "finding_suppression_is_not_repair",
                "changed_output_without_reaudit_is_not_success",
            ],
        }
        self.agent_material = build_responsibility_material(
            policy=self.policy,
            material_kind="agent_repair",
            audience_role_id="role.coding-agent",
            audit_ref=self.audit_before,
            subject_ref=self.subject,
            issue_class="implementation_defect",
            observed_facts=["The direct rule left func.performs unresolved."],
            evidence_refs=[_ref("evidence.before.finding")],
            limitations=["The proposed cause is a hypothesis until re-audit."],
            unresolved_scope=["Correct domain wording remains subject-owner material."],
            repair_targets=[self.target],
            available_actions=[
                {
                    "action_id": "action.edit-scenario",
                    "description": "Edit the bounded scenario text under existing authority.",
                    "required_right": "execute_authorized_repair",
                    "side_effect_class": "reversible_local",
                    "reaudit_required": True,
                }
            ],
            stop_conditions=["Stop if the edit changes intent or public authority."],
            escalation_conditions=["Escalate if more than one intent remains plausible."],
        )
        self.finding = {
            "finding_id": "finding.actor-role.1",
            "obligation_id": "func.performs",
            "before_outcome": "unresolved",
            "evidence_refs": [_ref("evidence.before.finding")],
            "limitations": ["Dependency evidence is not a human intent decision."],
            "repair_target": copy.deepcopy(self.target),
            "responsibility_material_ref": {
                "entity_id": self.agent_material["material_id"],
                "entity_digest": copy.deepcopy(self.agent_material["material_digest"]),
            },
        }
        self.cycle = build_repair_cycle(
            subject_ref=self.subject,
            before_audit_ref=self.audit_before,
            findings=[self.finding],
            responsibility_materials=[self.agent_material],
            responsibility_policy=self.policy,
        )

    def _attempt(self, *, changed: bool = True, self_report: bool = False) -> dict[str, object]:
        return record_repair_attempt(
            self.cycle,
            executed_by={
                "actor_id": "actor.coding-agent.1",
                "actor_class": "coding_agent",
                "identity_evidence_ref": _ref("identity.agent.1"),
            },
            authority_evidence_ref=_ref("authority.local-edit.1"),
            started_at="2026-07-16T02:00:00Z",
            completed_at="2026-07-16T02:01:00Z",
            before_subject_digest=self.subject["entity_digest"],
            after_subject_digest=_sha("after-subject" if changed else "before-subject"),
            change_evidence_refs=[_ref("change.diff.1")],
            stop_condition_result="not_triggered",
            self_report_ref=_ref("report.self.1") if self_report else None,
            responsibility_materials=[self.agent_material],
            responsibility_policy=self.policy,
        )

    def _assess(self, attempted: dict[str, object], **overrides: object) -> dict[str, object]:
        after_audit_ref = overrides.pop("after_audit_ref", _ref("audit.after.1"))
        finding_results = overrides.pop(
            "finding_results",
            [
                {
                    "finding_id": "finding.actor-role.1",
                    "before_outcome": "unresolved",
                    "after_outcome": "supported",
                    "effect": "resolved",
                    "reaudit_evidence_refs": [_ref("reaudit.finding.1")],
                }
            ],
        )
        regression_results = overrides.pop(
            "regression_results",
            [
                {
                    "guard_id": "guard.result-preserved",
                    "outcome": "passed",
                    "evidence_refs": [_ref("reaudit.guard.result")],
                },
                {
                    "guard_id": "guard.scope-preserved",
                    "outcome": "passed",
                    "evidence_refs": [_ref("reaudit.guard.scope")],
                },
            ],
        )
        attempt = attempted.get("repair_attempt")
        if attempt is not None:
            after_subject_ref = {
                "entity_id": attempted["subject_ref"]["entity_id"],
                "entity_version": attempted["subject_ref"]["entity_version"],
                "entity_digest": copy.deepcopy(attempt["after_subject_digest"]),
            }
            for result in finding_results:
                if "after_audit_result_ref" not in result:
                    evidence_ref = result["reaudit_evidence_refs"][0]
                    result["after_audit_result_ref"] = {
                        "result_id": evidence_ref["entity_id"],
                        "audit_ref": copy.deepcopy(after_audit_ref),
                        "subject_ref": copy.deepcopy(after_subject_ref),
                        "obligation_id": "func.performs",
                        "outcome": result["after_outcome"],
                        "result_locator": f"results/{evidence_ref['entity_id']}.json",
                        "result_digest": copy.deepcopy(evidence_ref["entity_digest"]),
                    }
            for result in regression_results:
                if "execution_result_ref" not in result:
                    evidence_ref = result["evidence_refs"][0]
                    result["execution_result_ref"] = {
                        "result_id": evidence_ref["entity_id"],
                        "audit_ref": copy.deepcopy(after_audit_ref),
                        "subject_ref": copy.deepcopy(after_subject_ref),
                        "guard_id": result["guard_id"],
                        "outcome": result["outcome"],
                        "result_locator": f"results/{evidence_ref['entity_id']}.json",
                        "result_digest": copy.deepcopy(evidence_ref["entity_digest"]),
                    }
        escalation_result = str(overrides.pop("escalation_result", "not_required"))
        limitations = overrides.pop("limitations", ["One bounded example only."])
        if "independent_review_refs" in overrides:
            independent_reviews = overrides.pop("independent_review_refs")
        else:
            review_basis = build_repair_effect_review_basis(
                attempted,
                after_audit_ref=after_audit_ref,
                finding_results=finding_results,
                regression_results=regression_results,
                escalation_result=escalation_result,
                limitations=limitations,
                responsibility_materials=[self.agent_material],
                responsibility_policy=self.policy,
            )
            independent_reviews = [
                build_independent_repair_review(
                    review_id="review.independent.1",
                    reviewer_identity=_vref(
                        "human.reviewer.1", "1", "human-reviewer"
                    ),
                    **review_basis,
                    reviewed_at="2026-07-16T02:30:00Z",
                    evidence_refs=[_ref("review.evidence.1")],
                    record_ref={
                        "record_id": "record.review.independent.1",
                        "record_locator": "reviews/independent-1.json",
                        "record_digest": _sha("independent-review-record"),
                    },
                    limitations=["External reviewer authenticity remains unproved."],
                )
            ]
        return assess_repair_effect(
            attempted,
            after_audit_ref=after_audit_ref,
            finding_results=finding_results,
            regression_results=regression_results,
            escalation_result=escalation_result,
            independent_review_refs=independent_reviews,
            limitations=limitations,
            responsibility_materials=[self.agent_material],
            responsibility_policy=self.policy,
        )

    def test_valid_policy_material_cycle_and_effect_are_replayable(self) -> None:
        validate_responsibility_policy(self.policy)
        validate_responsibility_material(self.agent_material, self.policy)
        validate_repair_cycle(self.cycle, [self.agent_material], self.policy)
        attempted = self._attempt()
        assessed = self._assess(attempted)
        validate_repair_cycle(assessed, [self.agent_material], self.policy)
        self.assertEqual(assessed["effect_assessment"]["overall_effect"], "improved")
        self.assertEqual(assessed["effect_assessment"]["field_repair_effect"], "not_evaluated")
        self.assertFalse(assessed["authority_boundary"]["executes_repair"])

    def test_pending_policy_cannot_emit_operational_material(self) -> None:
        pending = build_responsibility_policy(
            policy_id="policy.pending",
            policy_version="1",
            adoption_state="pending",
            roles=self.policy["roles"],
            issue_rules=self.policy["issue_rules"],
        )
        with self.assertRaisesRegex(RepairContractError, "externally adopted"):
            build_responsibility_material(
                policy=pending,
                material_kind="agent_repair",
                audience_role_id="role.coding-agent",
                audit_ref=self.audit_before,
                subject_ref=self.subject,
                issue_class="implementation_defect",
                observed_facts=["fact"],
                evidence_refs=[_ref("e")],
                limitations=["limit"],
                unresolved_scope=["unknown"],
                repair_targets=[self.target],
                available_actions=[{
                    "action_id": "a", "description": "edit", "required_right": "execute_authorized_repair", "side_effect_class": "reversible_local", "reaudit_required": True
                }],
                stop_conditions=["stop"],
                escalation_conditions=["escalate"],
            )

    def test_adopted_policy_requires_human_decision_record(self) -> None:
        broken = copy.deepcopy(self.policy)
        broken["human_decision_ref"] = None
        _reseal_policy(broken)
        with self.assertRaisesRegex(RepairContractError, "schema violation"):
            validate_responsibility_policy(broken)

    def test_agent_cannot_receive_human_only_right(self) -> None:
        broken = copy.deepcopy(self.policy)
        agent = next(
            item for item in broken["roles"] if item["role_id"] == "role.coding-agent"
        )
        agent["decision_rights"].append("final_acceptance")
        _reseal_policy(broken)
        with self.assertRaisesRegex(RepairContractError, "human-only"):
            validate_responsibility_policy(broken)

    def test_issue_rule_cannot_name_role_without_required_right(self) -> None:
        broken = copy.deepcopy(self.policy)
        rule = next(item for item in broken["issue_rules"] if item["issue_class"] == "implementation_defect")
        rule["permitted_role_ids"] = ["role.control-plane"]
        rule["accountable_role_id"] = "role.control-plane"
        _reseal_policy(broken)
        with self.assertRaisesRegex(RepairContractError, "lacks execute_authorized_repair"):
            validate_responsibility_policy(broken)

    def test_agent_material_prohibits_every_human_decision(self) -> None:
        broken = copy.deepcopy(self.agent_material)
        broken["prohibited_decisions"].remove("final_acceptance")
        _reseal_material(broken)
        with self.assertRaisesRegex(RepairContractError, "fails to prohibit"):
            validate_responsibility_material(broken, self.policy)

    def test_material_cannot_offer_external_action(self) -> None:
        broken = copy.deepcopy(self.agent_material)
        broken["available_actions"][0]["side_effect_class"] = "external"
        _reseal_material(broken)
        with self.assertRaisesRegex(RepairContractError, "external or irreversible"):
            validate_responsibility_material(broken, self.policy)

    def test_human_material_contains_question_not_prefilled_decision(self) -> None:
        material = build_responsibility_material(
            policy=self.policy,
            material_kind="human_decision",
            audience_role_id="role.requester",
            audit_ref=self.audit_before,
            subject_ref=self.subject,
            issue_class="scope_or_intent_choice",
            observed_facts=["Two interpretations remain compatible with the text."],
            evidence_refs=[_ref("evidence.interpretations")],
            limitations=["Engineering evidence cannot choose requester intent."],
            unresolved_scope=["Which interpretation expresses the intended value."],
            decision_questions=[{
                "question_id": "question.intent.1",
                "proposition": "Which declared interpretation is intended?",
                "required_right": "change_intent_or_scope",
                "options": ["Interpretation A", "Interpretation B"],
                "tradeoffs": ["A narrows the actor; B broadens the affected population."],
            }],
            stop_conditions=["Do not change the scope without the requester decision."],
            escalation_conditions=["The requester cannot determine the intended scope."],
        )
        self.assertNotIn("decision", material)
        self.assertFalse(material["routing_boundary"]["is_human_decision"])

    def test_human_question_must_match_policy_right(self) -> None:
        with self.assertRaisesRegex(RepairContractError, "differs from the adopted"):
            build_responsibility_material(
                policy=self.policy,
                material_kind="human_decision",
                audience_role_id="role.requester",
                audit_ref=self.audit_before,
                subject_ref=self.subject,
                issue_class="scope_or_intent_choice",
                observed_facts=["fact"],
                evidence_refs=[_ref("e")],
                limitations=["limit"],
                unresolved_scope=["unknown"],
                decision_questions=[{
                    "question_id": "q", "proposition": "Accept?", "required_right": "accept_residual_risk", "options": ["yes", "no"], "tradeoffs": ["risk"]
                }],
                stop_conditions=["stop"],
                escalation_conditions=["escalate"],
            )

    def test_repair_target_must_retain_anti_gaming_barriers(self) -> None:
        broken = copy.deepcopy(self.agent_material)
        broken["repair_targets"][0]["prohibited_shortcuts"] = [
            "changed_output_without_reaudit_is_not_success"
        ]
        _reseal_material(broken)
        with self.assertRaisesRegex(RepairContractError, "anti-gaming"):
            validate_responsibility_material(broken, self.policy)

    def test_cycle_rejects_material_substitution(self) -> None:
        substituted = copy.deepcopy(self.agent_material)
        substituted["observed_facts"] = ["A different fact."]
        _reseal_material(substituted)
        with self.assertRaisesRegex(RepairContractError, "no exact responsibility material"):
            validate_repair_cycle(self.cycle, [substituted], self.policy)

    def test_changed_output_is_not_success_without_after_audit(self) -> None:
        attempted = self._attempt()
        self.assertEqual(attempted["effect_assessment"]["status"], "not_assessed")
        self.assertEqual(attempted["effect_assessment"]["overall_effect"], "not_assessed")

    def test_effect_cannot_be_assessed_without_attempt(self) -> None:
        with self.assertRaisesRegex(RepairContractError, "without an attempt"):
            self._assess(self.cycle)

    def test_before_audit_cannot_be_replayed_as_after(self) -> None:
        with self.assertRaisesRegex(RepairContractError, "distinct observed"):
            self._assess(self._attempt(), after_audit_ref=self.audit_before)

    def test_self_report_alone_cannot_resolve_finding(self) -> None:
        attempted = self._attempt(self_report=True)
        with self.assertRaisesRegex(RepairContractError, "self-report alone"):
            self._assess(
                attempted,
                finding_results=[{
                    "finding_id": "finding.actor-role.1",
                    "before_outcome": "unresolved",
                    "after_outcome": "supported",
                    "effect": "resolved",
                    "reaudit_evidence_refs": [_ref("report.self.1")],
                }],
            )

    def test_finding_coverage_cannot_be_omitted(self) -> None:
        with self.assertRaisesRegex(RepairContractError, "cover every finding"):
            self._assess(self._attempt(), finding_results=[])

    def test_regression_guard_coverage_cannot_be_omitted(self) -> None:
        with self.assertRaisesRegex(RepairContractError, "cover every regression guard"):
            self._assess(self._attempt(), regression_results=[])

    def test_regression_failure_prevents_improved(self) -> None:
        results = [
            {
                "guard_id": "guard.result-preserved",
                "outcome": "failed",
                "evidence_refs": [_ref("regression.failure")],
            },
            {
                "guard_id": "guard.scope-preserved",
                "outcome": "passed",
                "evidence_refs": [_ref("regression.scope")],
            },
        ]
        assessed = self._assess(self._attempt(), regression_results=results)
        self.assertEqual(assessed["effect_assessment"]["overall_effect"], "mixed")

    def test_unchanged_subject_cannot_be_called_improved(self) -> None:
        assessed = self._assess(self._attempt(changed=False))
        self.assertEqual(assessed["effect_assessment"]["overall_effect"], "indeterminate")

    def test_before_outcome_substitution_is_rejected(self) -> None:
        with self.assertRaisesRegex(RepairContractError, "before outcome substitution"):
            self._assess(
                self._attempt(),
                finding_results=[{
                    "finding_id": "finding.actor-role.1",
                    "before_outcome": "refuted",
                    "after_outcome": "supported",
                    "effect": "resolved",
                    "reaudit_evidence_refs": [_ref("reaudit.finding.1")],
                }],
            )

    def test_cycle_digest_detects_effect_laundering(self) -> None:
        assessed = self._assess(self._attempt())
        broken = copy.deepcopy(assessed)
        broken["effect_assessment"]["overall_effect"] = "no_change"
        _reseal_cycle(broken)
        with self.assertRaisesRegex(RepairContractError, "overall repair effect mismatch"):
            validate_repair_cycle(broken, [self.agent_material], self.policy)

    def test_responsibility_decision_cannot_be_reused_after_policy_change(self) -> None:
        with self.assertRaisesRegex(RepairContractError, "target_basis_digest"):
            build_responsibility_policy(
                policy_id=self.policy["policy_id"],
                policy_version=self.policy["policy_version"],
                adoption_state="adopted",
                roles=self.policy["roles"],
                issue_rules=self.policy["issue_rules"],
                repair_effect_policy={
                    "transition_rule_id": "repair-effect-transition/v1",
                    "independent_review_required": False,
                },
                human_decision_ref=self.policy["human_decision_ref"],
            )

    def test_unresolved_after_outcome_cannot_be_laundered_as_resolved(self) -> None:
        with self.assertRaisesRegex(RepairContractError, "transition/v1"):
            self._assess(
                self._attempt(),
                finding_results=[
                    {
                        "finding_id": "finding.actor-role.1",
                        "before_outcome": "unresolved",
                        "after_outcome": "unresolved",
                        "effect": "resolved",
                        "reaudit_evidence_refs": [_ref("reaudit.finding.1")],
                    }
                ],
            )

    def test_independent_review_is_required_by_adopted_policy(self) -> None:
        with self.assertRaisesRegex(RepairContractError, "independent repair review"):
            self._assess(self._attempt(), independent_review_refs=[])

    def test_after_audit_result_must_bind_audit_subject_obligation_and_outcome(self) -> None:
        attempted = self._attempt()
        evidence_ref = _ref("reaudit.finding.1")
        after_subject = {
            "entity_id": attempted["subject_ref"]["entity_id"],
            "entity_version": attempted["subject_ref"]["entity_version"],
            "entity_digest": copy.deepcopy(
                attempted["repair_attempt"]["after_subject_digest"]
            ),
        }
        with self.assertRaisesRegex(RepairContractError, "binding mismatch"):
            self._assess(
                attempted,
                finding_results=[
                    {
                        "finding_id": "finding.actor-role.1",
                        "before_outcome": "unresolved",
                        "after_outcome": "supported",
                        "effect": "resolved",
                        "after_audit_result_ref": {
                            "result_id": evidence_ref["entity_id"],
                            "audit_ref": _ref("audit.wrong"),
                            "subject_ref": after_subject,
                            "obligation_id": "func.performs",
                            "outcome": "supported",
                            "result_locator": "results/reaudit.finding.1.json",
                            "result_digest": evidence_ref["entity_digest"],
                        },
                        "reaudit_evidence_refs": [evidence_ref],
                    }
                ],
            )

    def test_regression_result_must_bind_guard_and_after_subject(self) -> None:
        attempted = self._attempt()
        evidence_a = _ref("reaudit.guard.result")
        evidence_b = _ref("reaudit.guard.scope")
        after_subject = {
            "entity_id": attempted["subject_ref"]["entity_id"],
            "entity_version": attempted["subject_ref"]["entity_version"],
            "entity_digest": copy.deepcopy(
                attempted["repair_attempt"]["after_subject_digest"]
            ),
        }
        results = [
            {
                "guard_id": "guard.result-preserved",
                "outcome": "passed",
                "execution_result_ref": {
                    "result_id": evidence_a["entity_id"],
                    "audit_ref": _ref("audit.after.1"),
                    "subject_ref": after_subject,
                    "guard_id": "guard.wrong",
                    "outcome": "passed",
                    "result_locator": "results/reaudit.guard.result.json",
                    "result_digest": evidence_a["entity_digest"],
                },
                "evidence_refs": [evidence_a],
            },
            {
                "guard_id": "guard.scope-preserved",
                "outcome": "passed",
                "execution_result_ref": {
                    "result_id": evidence_b["entity_id"],
                    "audit_ref": _ref("audit.after.1"),
                    "subject_ref": after_subject,
                    "guard_id": "guard.scope-preserved",
                    "outcome": "passed",
                    "result_locator": "results/reaudit.guard.scope.json",
                    "result_digest": evidence_b["entity_digest"],
                },
                "evidence_refs": [evidence_b],
            },
        ]
        with self.assertRaisesRegex(RepairContractError, "binding mismatch"):
            self._assess(attempted, regression_results=results)

    def test_agent_identity_cannot_adopt_responsibility_policy(self) -> None:
        pending = build_responsibility_policy(
            policy_id=self.policy["policy_id"],
            policy_version=self.policy["policy_version"],
            adoption_state="pending",
            roles=self.policy["roles"],
            issue_rules=self.policy["issue_rules"],
            repair_effect_policy=self.policy["repair_effect_policy"],
        )
        agent_decision = copy.deepcopy(self.policy["human_decision_ref"])
        agent_decision["decided_by"] = "agent.worker"
        agent_decision["decision_maker_identity"] = _vref(
            "agent.worker", "1", "agent-worker"
        )
        agent_decision["decision_maker_kind"] = "coding_agent"
        with self.assertRaisesRegex(RepairContractError, "schema violation"):
            build_responsibility_policy(
                policy_id=pending["policy_id"],
                policy_version=pending["policy_version"],
                adoption_state="adopted",
                roles=pending["roles"],
                issue_rules=pending["issue_rules"],
                repair_effect_policy=pending["repair_effect_policy"],
                human_decision_ref=agent_decision,
            )

        mismatched = copy.deepcopy(self.policy["human_decision_ref"])
        mismatched["decided_by"] = "agent.worker"
        with self.assertRaisesRegex(RepairContractError, "identity does not match"):
            build_responsibility_policy(
                policy_id=pending["policy_id"],
                policy_version=pending["policy_version"],
                adoption_state="adopted",
                roles=pending["roles"],
                issue_rules=pending["issue_rules"],
                repair_effect_policy=pending["repair_effect_policy"],
                human_decision_ref=mismatched,
            )

    def test_placeholder_review_ref_is_not_a_typed_independent_review(self) -> None:
        with self.assertRaisesRegex(RepairContractError, "typed independent review"):
            self._assess(
                self._attempt(),
                independent_review_refs=[_ref("review.placeholder")],
            )

    def test_zero_digest_review_evidence_is_rejected(self) -> None:
        attempted = self._attempt()
        valid = self._assess(attempted)
        review = copy.deepcopy(
            valid["effect_assessment"]["independent_review_refs"][0]
        )
        review["evidence_refs"][0]["entity_digest"]["value"] = "0" * 64
        with self.assertRaisesRegex(RepairContractError, "zero placeholder digest"):
            self._assess(attempted, independent_review_refs=[review])

    def test_independent_review_requires_human_reviewer(self) -> None:
        attempted = self._attempt()
        valid = self._assess(attempted)
        review = copy.deepcopy(
            valid["effect_assessment"]["independent_review_refs"][0]
        )
        review["reviewer_kind"] = "coding_agent"
        with self.assertRaisesRegex(RepairContractError, "schema violation.*reviewer_kind"):
            self._assess(attempted, independent_review_refs=[review])

    def test_independent_review_targets_exact_effect_basis(self) -> None:
        attempted = self._attempt()
        valid = self._assess(attempted)
        review = copy.deepcopy(
            valid["effect_assessment"]["independent_review_refs"][0]
        )
        review["target_effect_basis_digest"] = _sha("other-effect-basis")
        _reseal_review(review)
        with self.assertRaisesRegex(RepairContractError, "another effect basis"):
            self._assess(attempted, independent_review_refs=[review])

    def test_independent_review_targets_exact_cycle_and_after_audit(self) -> None:
        attempted = self._attempt()
        valid = self._assess(attempted)
        original = valid["effect_assessment"]["independent_review_refs"][0]
        cases = (
            ("target_cycle_ref", "cycle_id", "repair-cycle.other", "cycle identity"),
            (
                "target_after_audit_ref",
                "entity_id",
                "audit.after.other",
                "after-audit record",
            ),
        )
        for container, field, value, message in cases:
            with self.subTest(container=container):
                review = copy.deepcopy(original)
                review[container][field] = value
                _reseal_review(review)
                with self.assertRaisesRegex(RepairContractError, message):
                    self._assess(attempted, independent_review_refs=[review])

    def test_independent_review_cannot_be_reused_for_another_attempt(self) -> None:
        first_attempt = self._attempt()
        valid = self._assess(first_attempt)
        review = copy.deepcopy(
            valid["effect_assessment"]["independent_review_refs"][0]
        )
        another_attempt = self._attempt(self_report=True)
        with self.assertRaisesRegex(RepairContractError, "cycle identity"):
            self._assess(another_attempt, independent_review_refs=[review])

    def test_independent_review_cannot_predate_repair_attempt(self) -> None:
        attempted = self._attempt()
        valid = self._assess(attempted)
        review = copy.deepcopy(
            valid["effect_assessment"]["independent_review_refs"][0]
        )
        review["reviewed_at"] = "2026-07-16T01:59:00Z"
        _reseal_review(review)
        with self.assertRaisesRegex(RepairContractError, "predates"):
            self._assess(attempted, independent_review_refs=[review])

    def test_legacy_repair_cycle_is_not_implicitly_accepted(self) -> None:
        for version in ("repair-cycle/v0", "repair-cycle/v1"):
            with self.subTest(version=version):
                broken = copy.deepcopy(self.cycle)
                broken["schema_version"] = version
                with self.assertRaisesRegex(RepairContractError, "schema violation"):
                    validate_repair_cycle(
                        broken, [self.agent_material], self.policy
                    )

    def test_legacy_responsibility_policy_is_not_implicitly_accepted(self) -> None:
        for version in ("responsibility-policy/v0", "responsibility-policy/v1"):
            with self.subTest(version=version):
                broken = copy.deepcopy(self.policy)
                broken["schema_version"] = version
                with self.assertRaisesRegex(RepairContractError, "schema violation"):
                    validate_responsibility_policy(broken)


if __name__ == "__main__":
    unittest.main()
