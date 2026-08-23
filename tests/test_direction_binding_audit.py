from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from dataclasses import replace
from io import StringIO
import hashlib
import json
import re
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator, ValidationError

from semantic_guard.cli import main as cli_main
from semantic_guard.direction_binding_audit import (
    _audit_id,
    _primary_evaluation,
    audit_direction_binding,
    validate_direction_binding_audit,
)
from semantic_guard.mcp_server import audit_direction_binding_service
from semantic_guard.providers import (
    AnalysisAttempt,
    ProviderAuthority,
    ProviderRequest,
    TokenCandidate,
)
from semantic_guard.public_contract import load_public_schema


RECORDED_AT = "2026-08-23T00:00:00Z"
SCALAR_MISSING = "この5人の中で、Cの次に体重が重い人は誰でしょうか？"
SCALAR_BOUND = "体重が重い順に並べたとき、" + SCALAR_MISSING
NON_SCALAR_MISSING = "横一列で、Aの次の項目はどれですか？"
NON_SCALAR_BOUND = "横一列を左から右へ辿るとき、Aの次の項目はどれですか？"


class CharacterMorphologyProvider:
    stage = "morphology"
    provider_id = "character-signal-test"
    provider_version = "1"
    resource_version = "fixture"
    split_mode = "C"

    def __init__(self, *, status: str = "ok") -> None:
        self.status = status
        self.calls = 0

    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        self.calls += 1
        tokens = []
        for match in re.finditer(r"体重|重い|軽い|\s+|.", request.text, re.DOTALL):
            surface = match.group(0)
            tokens.append(
                TokenCandidate(
                    surface=surface,
                    lemma=surface,
                    normalized=surface,
                    part_of_speech=("名詞", "普通名詞", "一般"),
                    start=match.start(),
                    end=match.end(),
                    features={"split_mode": self.split_mode},
                )
            )
        return AnalysisAttempt(
            stage=self.stage,
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            resource_version=self.resource_version,
            status=self.status,
            authority=ProviderAuthority(),
            requested_capabilities=request.requested_capabilities,
            fulfilled_capabilities=request.requested_capabilities,
            covered_spans=request.target_spans,
            tokens=tuple(tokens),
        )


class InvalidSplitProvider(CharacterMorphologyProvider):
    split_mode = "X"


class InvalidCoverageRoleProvider(CharacterMorphologyProvider):
    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        attempt = super().analyze(request)
        return replace(
            attempt,
            covered_spans=tuple(
                replace(span, role="forged") for span in attempt.covered_spans
            ),
        )


class FineGrainedMorphologyProvider(CharacterMorphologyProvider):
    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        self.calls += 1
        tokens = tuple(
            TokenCandidate(
                surface=surface,
                lemma=surface,
                normalized=surface,
                part_of_speech=("名詞",),
                start=index,
                end=index + 1,
                features={"split_mode": self.split_mode},
            )
            for index, surface in enumerate(request.text)
        )
        return AnalysisAttempt(
            stage=self.stage,
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            resource_version=self.resource_version,
            status=self.status,
            authority=ProviderAuthority(),
            requested_capabilities=request.requested_capabilities,
            fulfilled_capabilities=request.requested_capabilities,
            covered_spans=request.target_spans,
            tokens=tokens,
        )


class DiagnosticProvider(CharacterMorphologyProvider):
    provider_id = "diagnostic provider with spaces"

    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        attempt = super().analyze(request)
        return AnalysisAttempt(
            stage=attempt.stage,
            provider_id=attempt.provider_id,
            provider_version=attempt.provider_version,
            resource_version=attempt.resource_version,
            status=attempt.status,
            authority=attempt.authority,
            requested_capabilities=attempt.requested_capabilities,
            fulfilled_capabilities=attempt.fulfilled_capabilities,
            covered_spans=attempt.covered_spans,
            tokens=attempt.tokens,
            diagnostics=("provider warning",),
        )


class EmptyIdentityProvider(CharacterMorphologyProvider):
    provider_version = ""
    resource_version = ""


class LemmaVetoProvider(CharacterMorphologyProvider):
    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        attempt = super().analyze(request)
        return replace(
            attempt,
            tokens=tuple(
                replace(token, lemma="次ぐ") if token.surface == "次" else token
                for token in attempt.tokens
            ),
        )


class PartOfSpeechVetoProvider(CharacterMorphologyProvider):
    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        attempt = super().analyze(request)
        return replace(
            attempt,
            tokens=tuple(
                replace(token, part_of_speech=("動詞",))
                if token.surface == "重い"
                else token
                for token in attempt.tokens
            ),
        )


class JapaneseDiagnosticProvider(CharacterMorphologyProvider):
    provider_id = "日本語解析器"

    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        return replace(super().analyze(request), diagnostics=("警告",))


class DirectionBindingAuditTests(unittest.TestCase):
    def test_provider_free_default_is_indeterminate_not_pass(self) -> None:
        payload = audit_direction_binding(
            NON_SCALAR_MISSING,
            recorded_at=RECORDED_AT,
        )

        self.assertEqual(payload["execution"]["status"], "not_configured")
        self.assertEqual(payload["primary_rule_evaluation"]["state"], "indeterminate")
        self.assertEqual(payload["primary_rule_evaluation"]["emitter"], "none")
        self.assertEqual(payload["workflow_disposition"]["status"], "warn")
        validate_direction_binding_audit(payload)

    def test_scalar_gap_and_bound_are_projected_without_numeric_inference(self) -> None:
        provider = CharacterMorphologyProvider()
        missing = audit_direction_binding(
            SCALAR_MISSING,
            morphology_provider=provider,
            recorded_at=RECORDED_AT,
        )
        bound = audit_direction_binding(
            SCALAR_BOUND,
            morphology_provider=provider,
            recorded_at=RECORDED_AT,
        )

        self.assertEqual(missing["primary_rule_evaluation"]["state"], "gap")
        self.assertEqual(missing["primary_rule_evaluation"]["emitter"], "scalar")
        self.assertEqual(missing["workflow_disposition"]["status"], "warn")
        self.assertEqual(bound["primary_rule_evaluation"]["state"], "satisfied")
        self.assertEqual(bound["workflow_disposition"]["status"], "pass")
        self.assertEqual(provider.calls, 2)

    def test_non_scalar_gap_bound_and_conflict_are_projected(self) -> None:
        provider = CharacterMorphologyProvider()
        cases = (
            (NON_SCALAR_MISSING, "gap", "warn"),
            (NON_SCALAR_BOUND, "satisfied", "pass"),
            (
                "横一列を左から右へ又は右から左へ辿るとき、Aの次の項目はどれですか？",
                "conflict",
                "warn",
            ),
        )

        for text, state, workflow in cases:
            with self.subTest(state=state):
                payload = audit_direction_binding(
                    text,
                    morphology_provider=provider,
                    recorded_at=RECORDED_AT,
                )
                self.assertEqual(payload["primary_rule_evaluation"]["state"], state)
                self.assertEqual(payload["primary_rule_evaluation"]["emitter"], "non_scalar")
                self.assertEqual(payload["workflow_disposition"]["status"], workflow)

    def test_registered_expression_absence_is_not_applicable(self) -> None:
        payload = audit_direction_binding(
            "目的: 要求を明確にする。",
            morphology_provider=CharacterMorphologyProvider(),
            recorded_at=RECORDED_AT,
        )

        self.assertEqual(payload["primary_rule_evaluation"]["state"], "not_applicable")
        self.assertEqual(payload["workflow_disposition"]["status"], "pass")

    def test_executed_but_indeterminate_detector_never_becomes_pass(self) -> None:
        multiple_questions = audit_direction_binding(
            NON_SCALAR_MISSING + "\n" + NON_SCALAR_MISSING,
            morphology_provider=CharacterMorphologyProvider(),
            recorded_at=RECORDED_AT,
        )
        diagnostic = audit_direction_binding(
            NON_SCALAR_MISSING,
            morphology_provider=DiagnosticProvider(),
            recorded_at=RECORDED_AT,
        )

        for payload in (multiple_questions, diagnostic):
            self.assertEqual(payload["primary_rule_evaluation"]["state"], "indeterminate")
            self.assertEqual(payload["primary_rule_evaluation"]["emitter"], "none")
            self.assertEqual(payload["workflow_disposition"]["status"], "warn")
        self.assertRegex(
            diagnostic["execution"]["provider_ref"]["entity_id"],
            r"^provider\.[0-9a-f]{24}$",
        )

    def test_numeric_witness_does_not_change_primary_gap(self) -> None:
        provider = CharacterMorphologyProvider()
        rows = "A：50kg\nB：60kg\nC：70kg\nD：80kg\nE：90kg\n"
        without_rows = audit_direction_binding(
            SCALAR_MISSING,
            morphology_provider=provider,
            recorded_at=RECORDED_AT,
        )
        with_rows = audit_direction_binding(
            rows + SCALAR_MISSING,
            morphology_provider=provider,
            recorded_at=RECORDED_AT,
        )

        for field in (
            "state",
            "emitter",
            "needs_human_decision",
            "reason_codes",
            "numeric_evidence_role",
        ):
            self.assertEqual(
                without_rows["primary_rule_evaluation"][field],
                with_rows["primary_rule_evaluation"][field],
            )
        impact = with_rows["decision_frame_summary"]["frames"][0]["impact_evidence"]
        self.assertFalse(impact["affects_primary_finding"])

    def test_one_provider_attempt_is_shared_by_both_detectors(self) -> None:
        provider = CharacterMorphologyProvider()
        payload = audit_direction_binding(
            NON_SCALAR_MISSING,
            morphology_provider=provider,
            recorded_at=RECORDED_AT,
        )

        self.assertEqual(provider.calls, 1)
        self.assertEqual(
            payload["decision_frame_summary"]["morphology"],
            payload["direction_binding_summary"]["morphology"],
        )

    def test_partial_and_invalid_provider_results_fail_closed(self) -> None:
        partial = audit_direction_binding(
            NON_SCALAR_MISSING,
            morphology_provider=CharacterMorphologyProvider(status="partial"),
            recorded_at=RECORDED_AT,
        )
        invalid = audit_direction_binding(
            NON_SCALAR_MISSING,
            morphology_provider=InvalidSplitProvider(),
            recorded_at=RECORDED_AT,
        )
        invalid_role = audit_direction_binding(
            NON_SCALAR_MISSING,
            morphology_provider=InvalidCoverageRoleProvider(),
            recorded_at=RECORDED_AT,
        )

        self.assertEqual(partial["execution"]["status"], "partial")
        self.assertEqual(partial["primary_rule_evaluation"]["state"], "indeterminate")
        self.assertEqual(partial["workflow_disposition"]["status"], "warn")
        self.assertEqual(invalid["execution"]["status"], "invalid")
        self.assertEqual(invalid["primary_rule_evaluation"]["state"], "invalid")
        self.assertEqual(invalid["workflow_disposition"]["status"], "block")
        self.assertEqual(invalid_role["execution"]["status"], "invalid")
        self.assertEqual(invalid_role["primary_rule_evaluation"]["state"], "invalid")
        self.assertEqual(invalid_role["workflow_disposition"]["status"], "block")

    def test_multiple_primary_emitters_fail_closed_in_the_aggregator(self) -> None:
        scalar = audit_direction_binding(
            SCALAR_MISSING,
            morphology_provider=CharacterMorphologyProvider(),
            recorded_at=RECORDED_AT,
        )["decision_frame_summary"]
        non_scalar = audit_direction_binding(
            NON_SCALAR_MISSING,
            morphology_provider=CharacterMorphologyProvider(),
            recorded_at=RECORDED_AT,
        )["direction_binding_summary"]
        evaluation, workflow = _primary_evaluation(
            scalar,
            non_scalar,
            execution_status="executed",
        )

        self.assertEqual(evaluation["state"], "invalid")
        self.assertEqual(evaluation["emitter"], "none")
        self.assertIn("multiple_primary_emitters", evaluation["reason_codes"])
        self.assertEqual(workflow, "block")

    def test_identity_gaps_and_context_only_operations_fail_closed(self) -> None:
        empty_identity = audit_direction_binding(
            NON_SCALAR_BOUND,
            morphology_provider=EmptyIdentityProvider(),
            recorded_at=RECORDED_AT,
        )
        context_only = audit_direction_binding(
            "目的: 別件",
            context=NON_SCALAR_BOUND,
            morphology_provider=CharacterMorphologyProvider(),
            recorded_at=RECORDED_AT,
        )
        empty_text_context_only = audit_direction_binding(
            "",
            context=NON_SCALAR_BOUND,
            morphology_provider=CharacterMorphologyProvider(),
            recorded_at=RECORDED_AT,
        )

        for payload in (empty_identity, context_only, empty_text_context_only):
            self.assertEqual(payload["primary_rule_evaluation"]["state"], "invalid")
            self.assertEqual(payload["primary_rule_evaluation"]["emitter"], "none")
            self.assertEqual(payload["execution"]["status"], "invalid")
            self.assertEqual(payload["workflow_disposition"]["status"], "block")

    def test_signal_only_morphology_cannot_veto_a_surface_candidate(self) -> None:
        payloads = (
            audit_direction_binding(
                NON_SCALAR_MISSING,
                morphology_provider=LemmaVetoProvider(),
                recorded_at=RECORDED_AT,
            ),
            audit_direction_binding(
                SCALAR_MISSING,
                morphology_provider=PartOfSpeechVetoProvider(),
                recorded_at=RECORDED_AT,
            ),
        )

        for payload in payloads:
            self.assertEqual(payload["execution"]["status"], "executed")
            self.assertEqual(payload["primary_rule_evaluation"]["state"], "indeterminate")
            self.assertEqual(payload["primary_rule_evaluation"]["emitter"], "none")
            self.assertEqual(payload["workflow_disposition"]["status"], "warn")
            self.assertIn(
                "morphology_signal_surface_candidate_unresolved",
                payload["primary_rule_evaluation"]["reason_codes"],
            )

    def test_fine_grained_signal_only_tokens_do_not_break_public_validation(self) -> None:
        payload = audit_direction_binding(
            "体重が重い順ではなく軽い順に並べたとき、基準の次に体重が重いものはどれですか？",
            morphology_provider=FineGrainedMorphologyProvider(),
            recorded_at=RECORDED_AT,
        )

        self.assertEqual(payload["decision_frame_summary"]["status"], "indeterminate")
        self.assertEqual(payload["primary_rule_evaluation"]["state"], "indeterminate")
        self.assertEqual(payload["workflow_disposition"]["status"], "warn")
        validate_direction_binding_audit(
            payload,
            text="体重が重い順ではなく軽い順に並べたとき、基準の次に体重が重いものはどれですか？",
            context="",
        )

    def test_non_ascii_provider_material_is_hash_normalized(self) -> None:
        payload = audit_direction_binding(
            NON_SCALAR_MISSING,
            morphology_provider=JapaneseDiagnosticProvider(),
            recorded_at=RECORDED_AT,
        )

        self.assertRegex(
            payload["execution"]["provider_ref"]["entity_id"],
            r"^provider\.[0-9a-f]{24}$",
        )
        self.assertTrue(
            all(reason.isascii() for reason in payload["primary_rule_evaluation"]["reason_codes"])
        )
        validate_direction_binding_audit(payload, source_text=NON_SCALAR_MISSING)

    def test_unsupported_attached_scalar_direction_is_indeterminate(self) -> None:
        for prefix in (
            "体重が増える順に並べたとき、",
            "体重が増える順に整列したとき、",
            "体重が増える順にソートしたとき、",
            "体重が増える順で並べたとき、",
            "体重が重い順に厳密に並べたとき、",
            "体重が重い順または軽い順に並べたとき、",
        ):
            with self.subTest(prefix=prefix):
                payload = audit_direction_binding(
                    prefix + "基準の次に体重が重いものはどれですか？",
                    morphology_provider=CharacterMorphologyProvider(),
                    recorded_at=RECORDED_AT,
                )

                self.assertEqual(payload["decision_frame_summary"]["status"], "indeterminate")
                self.assertEqual(payload["primary_rule_evaluation"]["state"], "indeterminate")
                self.assertEqual(payload["workflow_disposition"]["status"], "warn")

    def test_quoted_block_and_unbalanced_direction_sources_never_pass(self) -> None:
        cases = (
            "「例。体重が重い順に並べたとき、Cの次に体重が重い人は誰？」",
            "「例。横一列を左から右へ辿るとき、Aの次の項目はどれ？」",
            "> 例。体重が重い順に並べたとき、Cの次に体重が重い人は誰？",
            "> 例。横一列を左から右へ辿るとき、Aの次の項目はどれ？",
            "横一列を左から右へ」辿るとき、Aの次の項目はどれですか？",
        )
        for text in cases:
            with self.subTest(text=text):
                payload = audit_direction_binding(
                    text,
                    morphology_provider=CharacterMorphologyProvider(),
                    recorded_at=RECORDED_AT,
                )

                self.assertEqual(payload["primary_rule_evaluation"]["state"], "indeterminate")
                self.assertEqual(payload["primary_rule_evaluation"]["emitter"], "none")
                self.assertEqual(payload["workflow_disposition"]["status"], "warn")

    def test_source_provenance_and_replay_tampering_is_rejected(self) -> None:
        payload = audit_direction_binding(
            NON_SCALAR_BOUND,
            morphology_provider=CharacterMorphologyProvider(),
            recorded_at=RECORDED_AT,
        )
        mutations = {
            "subject": lambda item: item["subject_ref"].update(entity_id="other.subject"),
            "producer": lambda item: item["producer_ref"].update(entity_id="other.producer"),
            "execution": lambda item: item["execution"].update(status="partial"),
            "coverage-role": lambda item: item["execution"]["covered_regions"][0].update(role="forged"),
            "excerpt": lambda item: item["direction_binding_summary"]["frames"][0]["source_span"].update(excerpt="偽"),
            "reference": lambda item: item["direction_binding_summary"]["frames"][0]["operation"].update(reference_label="偽"),
            "provider": lambda item: item["direction_binding_summary"]["morphology"].update(provider_id="other-provider"),
            "reason": lambda item: item["primary_rule_evaluation"].update(reason_codes=["forged.reason"]),
            "human-decision": lambda item: item["primary_rule_evaluation"].update(needs_human_decision=True),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                tampered = deepcopy(payload)
                mutate(tampered)
                if name == "reason":
                    tampered["workflow_disposition"]["reason_codes"] = ["forged.reason"]
                tampered["audit_id"] = _audit_id(tampered)
                with self.assertRaises(ValidationError):
                    validate_direction_binding_audit(
                        tampered,
                        source_text=NON_SCALAR_BOUND,
                    )

    def test_no_frame_and_text_context_role_forgery_is_rejected(self) -> None:
        unrelated = audit_direction_binding(
            "目的: 要求を明確にする。",
            morphology_provider=CharacterMorphologyProvider(),
            recorded_at=RECORDED_AT,
        )
        forged = deepcopy(unrelated)
        for key in ("decision_frame_summary", "direction_binding_summary"):
            forged[key]["status"] = "indeterminate"
            forged[key]["derivation_status"] = "blocked_by_unknown"
            forged[key]["frames"] = []
            forged[key]["unknown_reasons"] = ["forged_reason"]
        forged["primary_rule_evaluation"].update(
            state="indeterminate",
            emitter="none",
            needs_human_decision=True,
            basis_frame_ids=[],
            reason_codes=["forged_reason"],
        )
        forged["workflow_disposition"].update(
            status="warn",
            reason_codes=["forged_reason"],
        )
        forged["audit_id"] = _audit_id(forged)
        with self.assertRaises(ValidationError):
            validate_direction_binding_audit(
                forged,
                source_text="目的: 要求を明確にする。",
            )

        source_only = audit_direction_binding(
            NON_SCALAR_BOUND,
            morphology_provider=CharacterMorphologyProvider(),
            recorded_at=RECORDED_AT,
        )
        validate_direction_binding_audit(source_only, source_text=NON_SCALAR_BOUND)
        with self.assertRaisesRegex(ValidationError, "input region roles"):
            validate_direction_binding_audit(
                source_only,
                text="",
                context=NON_SCALAR_BOUND,
            )

    def test_identity_binds_time_context_source_and_result(self) -> None:
        context = "候補集合は現在の表だけを使う。"
        provider = CharacterMorphologyProvider()
        first = audit_direction_binding(
            NON_SCALAR_MISSING,
            context=context,
            morphology_provider=provider,
            recorded_at=RECORDED_AT,
        )
        second = audit_direction_binding(
            NON_SCALAR_MISSING,
            context=context,
            morphology_provider=provider,
            recorded_at=RECORDED_AT,
        )
        combined = NON_SCALAR_MISSING + "\n" + context

        self.assertEqual(first, second)
        self.assertEqual(
            first["source_digest"]["value"],
            hashlib.sha256(combined.encode("utf-8")).hexdigest(),
        )
        self.assertEqual([item["role"] for item in first["input_regions"]], ["source_text", "context"])
        validate_direction_binding_audit(first, source_text=combined)
        with self.assertRaisesRegex(ValidationError, "source_digest"):
            validate_direction_binding_audit(first, source_text=combined + "x")

    def test_tampering_is_rejected_by_schema_and_cross_field_checks(self) -> None:
        payload = audit_direction_binding(
            "A：50kg\nB：60kg\nC：70kg\nD：80kg\nE：90kg\n" + SCALAR_MISSING,
            morphology_provider=CharacterMorphologyProvider(),
            recorded_at=RECORDED_AT,
        )
        tampered = deepcopy(payload)
        tampered["decision_frame_summary"]["frames"][0]["impact_evidence"][
            "affects_primary_finding"
        ] = True
        tampered["audit_id"] = _audit_id(tampered)
        with self.assertRaises(ValidationError):
            validate_direction_binding_audit(tampered)

        extra = deepcopy(payload)
        extra["unexpected"] = True
        extra["audit_id"] = _audit_id(extra)
        with self.assertRaises(ValidationError):
            validate_direction_binding_audit(extra)

    def test_cli_and_mcp_have_identical_public_projection(self) -> None:
        output = StringIO()
        with (
            patch(
                "semantic_guard.cli.SudachiMorphologyProvider",
                CharacterMorphologyProvider,
            ),
            redirect_stdout(output),
        ):
            cli_status = cli_main(
                (
                    "audit-direction-binding",
                    "--text",
                    NON_SCALAR_BOUND,
                    "--morphology",
                    "sudachi",
                    "--recorded-at",
                    RECORDED_AT,
                )
            )
        with patch(
            "semantic_guard.mcp_server.SudachiMorphologyProvider",
            CharacterMorphologyProvider,
        ):
            mcp_payload = audit_direction_binding_service(
                NON_SCALAR_BOUND,
                morphology="sudachi",
                recorded_at=RECORDED_AT,
            )

        self.assertEqual(cli_status, 0)
        self.assertEqual(json.loads(output.getvalue()), mcp_payload)

    def test_cli_fail_on_changes_only_exit_status(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            status = cli_main(
                (
                    "audit-direction-binding",
                    "--text",
                    NON_SCALAR_MISSING,
                    "--recorded-at",
                    RECORDED_AT,
                    "--fail-on",
                    "warn",
                )
            )

        payload = json.loads(output.getvalue())
        self.assertEqual(status, 3)
        self.assertEqual(payload["primary_rule_evaluation"]["state"], "indeterminate")
        self.assertEqual(payload["workflow_disposition"]["status"], "warn")

    def test_cli_rejects_invalid_recorded_at_without_traceback(self) -> None:
        for value in ("not-a-time", ""):
            with self.subTest(value=value):
                error = StringIO()
                with redirect_stderr(error), self.assertRaises(SystemExit) as raised:
                    cli_main(
                        (
                            "audit-direction-binding",
                            "--text",
                            NON_SCALAR_MISSING,
                            "--recorded-at",
                            value,
                        )
                    )

                self.assertEqual(raised.exception.code, 2)
                self.assertIn("recorded_at must be an RFC 3339 date-time string", error.getvalue())
                self.assertNotIn("Traceback", error.getvalue())

        for value in (0, False):
            with self.subTest(value=value), self.assertRaises(TypeError):
                audit_direction_binding(NON_SCALAR_MISSING, recorded_at=value)  # type: ignore[arg-type]

    def test_public_schema_is_registered_and_closed(self) -> None:
        schema = load_public_schema("direction-binding-audit")

        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "semantic-guard-direction-binding-audit/v1",
        )
        self.assertFalse(schema["unevaluatedProperties"])

        payload = audit_direction_binding(
            NON_SCALAR_MISSING,
            morphology_provider=CharacterMorphologyProvider(),
            recorded_at=RECORDED_AT,
        )
        wrong_workflow = deepcopy(payload)
        wrong_workflow["workflow_disposition"]["status"] = "block"
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema).validate(wrong_workflow)

        partial_satisfied = audit_direction_binding(
            NON_SCALAR_BOUND,
            morphology_provider=CharacterMorphologyProvider(),
            recorded_at=RECORDED_AT,
        )
        partial_satisfied["execution"]["status"] = "partial"
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema).validate(partial_satisfied)

        satisfied_warn = audit_direction_binding(
            NON_SCALAR_BOUND,
            morphology_provider=CharacterMorphologyProvider(),
            recorded_at=RECORDED_AT,
        )
        satisfied_warn["workflow_disposition"]["status"] = "warn"
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema).validate(satisfied_warn)


if __name__ == "__main__":
    unittest.main()
