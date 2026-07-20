from __future__ import annotations

import unittest

from semantic_guard.lifecycle_trace import (
    STAGES,
    LifecycleTraceValidationError,
    build_composition_edge,
    build_lifecycle_node,
    build_lifecycle_trace,
    build_pair_preservation,
    digest_value,
    lifecycle_trace_errors,
    validate_lifecycle_trace,
    versioned_ref,
)


RECORDED_AT = "2026-07-16T14:30:00+09:00"


def _evidence(
    evidence_id: str,
    *,
    trust_level: str = "tool_observed",
    freshness: str = "current",
) -> dict:
    return {
        "evidence_id": evidence_id,
        "locator": f"artifact://{evidence_id}",
        "digest": digest_value({"evidence": evidence_id}),
        "trust_level": trust_level,
        "freshness": {
            "observed_at": RECORDED_AT,
            "valid_until": None,
            "status": freshness,
        },
        "limitations": ["Fixture evidence proves only deterministic composition behavior."],
    }


def _obligations(primary_state: str, *, verified: bool = False) -> list[dict]:
    return [
        {
            "obligation_id": "obligation.primary",
            "required": True,
            "state": primary_state,
            "basis_evidence_refs": ["evidence.verification"] if verified else [],
            "rule_refs": ["rule.lifecycle.primary@v1"],
        },
        {
            "obligation_id": "obligation.secondary",
            "required": False,
            "state": "carried" if primary_state != "active" else "active",
            "basis_evidence_refs": [],
            "rule_refs": ["rule.lifecycle.primary@v1"],
        },
    ]


def _valid_trace() -> dict:
    subject = {
        "snapshot_ref": "subject.snapshot.request.v1",
        "digest": digest_value({"request": "preserved subject"}),
    }
    proposition = {
        "proposition_id": "proposition.deliver-bounded-change",
        "digest": digest_value({"proposition": "deliver bounded change"}),
    }
    profiles = [versioned_ref("profile.lifecycle.fixture", "v1")]
    rules = [
        versioned_ref("rule.lifecycle.primary", "v1"),
        versioned_ref("rule.lifecycle.resolve", "v1"),
    ]
    actor = {"actor_id": "agent.fixture", "actor_kind": "ai_agent", "role": "worker"}
    observer = {
        "observer_id": "observer.fixture",
        "observer_kind": "system",
        "relationship_to_actor": "same_process",
        "trust_class": "tool_observed",
    }
    request_evidence = _evidence("evidence.request")
    verification_evidence = _evidence("evidence.verification")

    nodes: list[dict] = []
    for index, stage in enumerate(STAGES[:-2]):
        nodes.append(
            build_lifecycle_node(
                stage=stage,
                subject=subject,
                proposition=proposition,
                obligation_states=_obligations("active" if index == 0 else "carried"),
                unresolved_refs=["unresolved.primary"],
                evidence_refs=[request_evidence],
                authority_rights=["read_subject"],
                profile_refs=profiles,
                rule_refs=rules,
                actor=actor,
                observer=observer,
                recorded_at=RECORDED_AT,
            )
        )

    verification = build_lifecycle_node(
        stage="verification",
        subject=subject,
        proposition=proposition,
        obligation_states=_obligations("resolved", verified=True),
        unresolved_refs=[],
        evidence_refs=[request_evidence, verification_evidence],
        authority_rights=["read_subject"],
        profile_refs=profiles,
        rule_refs=rules,
        actor=actor,
        observer=observer,
        recorded_at=RECORDED_AT,
    )
    nodes.append(verification)
    completion = build_lifecycle_node(
        stage="completion_claim",
        subject=subject,
        proposition=proposition,
        obligation_states=_obligations("resolved", verified=True),
        unresolved_refs=[],
        evidence_refs=[request_evidence, verification_evidence],
        authority_rights=["read_subject"],
        profile_refs=profiles,
        rule_refs=rules,
        actor=actor,
        observer=observer,
        recorded_at=RECORDED_AT,
        completion={
            "verification_node_refs": [verification["node_id"]],
            "obligation_trace": [
                {
                    "obligation_id": "obligation.primary",
                    "required": True,
                    "state": "resolved",
                    "source_node_ref": verification["node_id"],
                    "verification_node_ref": verification["node_id"],
                }
            ],
            "residual_unproven_scope": [],
            "human_acceptance": {"status": "pending", "authority_record_ref": None},
        },
    )
    nodes.append(completion)

    resolution_id = "resolution.primary.verified"
    resolution_record = {
        "resolution_id": resolution_id,
        "status": "resolved",
        "obligation_id": "obligation.primary",
        "unresolved_refs": ["unresolved.primary"],
        "input_node_ref": nodes[7]["node_id"],
        "output_node_ref": verification["node_id"],
        "evidence_refs": ["evidence.verification"],
        "rule_ref": versioned_ref("rule.lifecycle.resolve", "v1"),
        "human_authority_record_ref": None,
        "rationale": "Located verification evidence closes the bounded fixture obligation.",
        "recorded_at": RECORDED_AT,
    }

    edge_kinds = (
        "refines",
        "derives",
        "transforms",
        "transforms",
        "transforms",
        "derives",
        "transforms",
        "verifies",
        "completes",
    )
    edges: list[dict] = []
    for index, (input_node, output_node, edge_kind) in enumerate(
        zip(nodes[:-1], nodes[1:], edge_kinds, strict=True)
    ):
        obligation_transitions = None
        unresolved_transitions = None
        allowed_changes: list[str] = []
        evidence_refs: list[str] = []
        if edge_kind == "verifies":
            obligation_transitions = {
                "obligation.primary": {
                    "transition": "resolved",
                    "resolution_record_ref": resolution_id,
                }
            }
            unresolved_transitions = {
                "unresolved.primary": {
                    "status": "resolved",
                    "resolution_record_ref": resolution_id,
                }
            }
            allowed_changes = ["resolution"]
            evidence_refs = ["evidence.verification"]
        edges.append(
            build_composition_edge(
                edge_kind=edge_kind,
                composition_rule_id=f"composition.stage-{index}",
                composition_rule_version="v1",
                input_node_refs=[input_node["node_id"]],
                output_node_refs=[output_node["node_id"]],
                preservation=build_pair_preservation(
                    input_node,
                    output_node,
                    obligation_transitions=obligation_transitions,
                    unresolved_transitions=unresolved_transitions,
                ),
                allowed_changes=allowed_changes,
                evidence_refs=evidence_refs,
            )
        )
    return build_lifecycle_trace(
        trace_id="lifecycle-trace.fixture-linear",
        nodes=nodes,
        edges=edges,
        resolution_records=[resolution_record],
    )


class LifecycleTraceTests(unittest.TestCase):
    @staticmethod
    def _codes(trace: dict) -> set[str]:
        return {item["code"] for item in lifecycle_trace_errors(trace)}

    @staticmethod
    def _node(trace: dict, stage: str) -> dict:
        return next(item for item in trace["nodes"] if item["stage"] == stage)

    def test_valid_trace_replays_and_build_is_deterministic(self) -> None:
        first = _valid_trace()
        second = _valid_trace()
        self.assertEqual(first, second)
        self.assertEqual(validate_lifecycle_trace(first), first)
        self.assertEqual(
            {item["stage"] for item in first["nodes"]},
            set(STAGES),
        )
        self.assertEqual(
            self._node(first, "completion_claim")["completion"]["human_acceptance"]["status"],
            "pending",
        )

    def test_subject_substitution_is_rejected(self) -> None:
        trace = _valid_trace()
        target = self._node(trace, "requirement")
        target["subject"] = {
            "snapshot_ref": "subject.snapshot.substituted",
            "digest": digest_value({"different": "subject"}),
        }
        self.assertIn("subject_substitution_without_authority", self._codes(trace))

    def test_proposition_substitution_is_rejected(self) -> None:
        trace = _valid_trace()
        target = self._node(trace, "plan")
        target["proposition"] = {
            "proposition_id": "proposition.changed-intent",
            "digest": digest_value({"intent": "changed"}),
        }
        self.assertIn("proposition_substitution_without_authority", self._codes(trace))

    def test_required_obligation_cannot_disappear(self) -> None:
        trace = _valid_trace()
        target = self._node(trace, "plan")
        target["obligation_states"] = [
            item
            for item in target["obligation_states"]
            if item["obligation_id"] != "obligation.primary"
        ]
        self.assertIn("obligation_dropped_without_authority", self._codes(trace))

    def test_unresolved_item_cannot_disappear(self) -> None:
        trace = _valid_trace()
        self._node(trace, "plan")["unresolved_refs"] = []
        self.assertIn("unresolved_dropped_without_resolution", self._codes(trace))

    def test_fake_resolution_without_located_record_is_rejected(self) -> None:
        trace = _valid_trace()
        trace["resolution_records"] = []
        self.assertIn("resolution_record_missing", self._codes(trace))

    def test_trust_and_freshness_promotions_require_authority(self) -> None:
        for field, promoted_value, expected_code in (
            (
                "trust_level",
                "independently_observed",
                "evidence_trust_promotion_without_authority",
            ),
            (
                "freshness",
                {
                    "observed_at": RECORDED_AT,
                    "valid_until": None,
                    "status": "current",
                },
                "evidence_freshness_promotion_without_authority",
            ),
        ):
            with self.subTest(field=field):
                trace = _valid_trace()
                target = self._node(trace, "plan")
                evidence = next(
                    item for item in target["evidence_refs"] if item["evidence_id"] == "evidence.request"
                )
                if field == "freshness":
                    source = self._node(trace, "decision")
                    next(
                        item
                        for item in source["evidence_refs"]
                        if item["evidence_id"] == "evidence.request"
                    )["freshness"]["status"] = "unknown"
                else:
                    evidence[field] = promoted_value
                self.assertIn(expected_code, self._codes(trace))

    def test_authority_escalation_requires_human_grant_record(self) -> None:
        trace = _valid_trace()
        self._node(trace, "plan")["authority_rights"].append("write_external")
        self.assertIn("authority_escalation_unmapped", self._codes(trace))

    def test_incomplete_merge_is_rejected(self) -> None:
        trace = _valid_trace()
        edge = next(
            item
            for item in trace["edges"]
            if self._node(trace, "decision")["node_id"] in item["input_node_refs"]
        )
        edge["edge_kind"] = "merges"
        edge["input_node_refs"].append(self._node(trace, "requirement")["node_id"])
        self.assertIn("incomplete_merge_preservation", self._codes(trace))

    def test_cycle_is_rejected(self) -> None:
        trace = _valid_trace()
        edge = next(item for item in trace["edges"] if item["edge_kind"] == "completes")
        edge["output_node_refs"] = [self._node(trace, "request")["node_id"]]
        self.assertIn("lifecycle_cycle_detected", self._codes(trace))

    def test_completion_requires_connected_verification(self) -> None:
        trace = _valid_trace()
        completion = self._node(trace, "completion_claim")["completion"]
        completion["verification_node_refs"] = [self._node(trace, "diff")["node_id"]]
        self.assertIn("completion_verification_invalid", self._codes(trace))

    def test_final_acceptance_cannot_be_laundered(self) -> None:
        trace = _valid_trace()
        acceptance = self._node(trace, "completion_claim")["completion"]["human_acceptance"]
        acceptance["status"] = "accepted"
        acceptance["authority_record_ref"] = None
        self.assertIn("final_acceptance_authority_missing", self._codes(trace))

    def test_stage_nodes_without_composition_are_not_success(self) -> None:
        trace = _valid_trace()
        trace["edges"] = trace["edges"][:1]
        codes = self._codes(trace)
        self.assertTrue(
            {"node_not_composed_from_request", "node_not_composed_to_completion"} & codes
        )

    def test_exception_exposes_typed_codes(self) -> None:
        trace = _valid_trace()
        self._node(trace, "plan")["unresolved_refs"] = []
        with self.assertRaises(LifecycleTraceValidationError) as caught:
            validate_lifecycle_trace(trace)
        self.assertIn("unresolved_dropped_without_resolution", caught.exception.codes)


if __name__ == "__main__":
    unittest.main()
