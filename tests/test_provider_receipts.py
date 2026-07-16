from __future__ import annotations

from dataclasses import replace
import unittest

from semantic_guard.provider_receipts import (
    AnalyzerQualification,
    EMPTY_QUALIFIED_ANALYZER_REGISTRY,
    QualifiedAnalyzerRegistry,
    build_provider_execution_receipt,
)
from semantic_guard.providers import (
    AnalysisAttempt,
    AnalysisSpan,
    ProviderAuthority,
    ProviderRequest,
    TokenCandidate,
)
from semantic_guard.reassessment import REQUIRED_CAPABILITIES, policy_scope


class ProviderReceiptTests(unittest.TestCase):
    def material(self, text: str = "利用者が検索する") -> tuple[ProviderRequest, AnalysisAttempt]:
        request = ProviderRequest(
            text=text,
            target_spans=(AnalysisSpan(0, len(text), "scenario"),),
            reason_codes=("scenario_actor_role_not_assertion_capable",),
            requested_capabilities=REQUIRED_CAPABILITIES,
            upstream_tokens=(
                TokenCandidate("利用者", "利用者", "利用者", ("NOUN",), 0, 3),
            ),
        )
        attempt = AnalysisAttempt(
            stage="dependency_parse",
            provider_id="qualified-fixture",
            provider_version="1",
            resource_version="model-1",
            status="ok",
            authority=ProviderAuthority(),
            requested_capabilities=request.requested_capabilities,
            fulfilled_capabilities=request.requested_capabilities,
            covered_spans=request.target_spans,
            upstream_usage=("upstream_tokens:ignored_independent_reparse",),
        )
        return request, attempt

    def qualification(self, **changes: str) -> AnalyzerQualification:
        values = {
            "provider_id": "qualified-fixture",
            "provider_version": "1",
            "resource_version": "model-1",
            "policy_scope": policy_scope("func.performs"),
        }
        values.update(changes)
        return AnalyzerQualification(
            **values,
            capabilities=REQUIRED_CAPABILITIES,
            qualification_basis="controlled fixture qualification",
        )

    def test_receipt_binds_source_request_output_and_upstream_usage(self) -> None:
        request, attempt = self.material()
        receipt = build_provider_execution_receipt(request, attempt)

        self.assertTrue(receipt.source_digest.startswith("sha256:"))
        self.assertTrue(receipt.request_digest.startswith("sha256:"))
        self.assertTrue(receipt.output_digest.startswith("sha256:"))
        self.assertEqual(
            receipt.upstream_usage,
            ("upstream_tokens:ignored_independent_reparse",),
        )
        changed_source = build_provider_execution_receipt(*self.material("管理者が検索する"))
        changed_output = build_provider_execution_receipt(
            request,
            replace(attempt, diagnostics=("changed",)),
        )
        changed_request = build_provider_execution_receipt(
            replace(request, reason_codes=("changed-reason",)),
            attempt,
        )
        self.assertNotEqual(receipt.receipt_id, changed_source.receipt_id)
        self.assertNotEqual(receipt.receipt_id, changed_output.receipt_id)
        self.assertNotEqual(receipt.receipt_id, changed_request.receipt_id)

    def test_registry_is_empty_and_fail_closed_by_default(self) -> None:
        request, attempt = self.material()
        receipt = build_provider_execution_receipt(request, attempt)

        self.assertIsNone(
            EMPTY_QUALIFIED_ANALYZER_REGISTRY.match(
                receipt,
                required_capabilities=REQUIRED_CAPABILITIES,
                policy_scope=policy_scope("func.performs"),
            )
        )

    def test_qualification_requires_exact_identity_capability_and_scope(self) -> None:
        request, attempt = self.material()
        receipt = build_provider_execution_receipt(request, attempt)
        registry = QualifiedAnalyzerRegistry((self.qualification(),))

        self.assertIsNotNone(
            registry.match(
                receipt,
                required_capabilities=REQUIRED_CAPABILITIES,
                policy_scope=policy_scope("func.performs"),
            )
        )
        self.assertIsNone(
            QualifiedAnalyzerRegistry(
                (self.qualification(provider_version="2"),)
            ).match(
                receipt,
                required_capabilities=REQUIRED_CAPABILITIES,
                policy_scope=policy_scope("func.performs"),
            )
        )
        self.assertIsNone(
            registry.match(
                receipt,
                required_capabilities=(*REQUIRED_CAPABILITIES, "scope"),
                policy_scope=policy_scope("func.performs"),
            )
        )
        self.assertIsNone(
            registry.match(
                receipt,
                required_capabilities=REQUIRED_CAPABILITIES,
                policy_scope=policy_scope("func.acts_on"),
            )
        )


if __name__ == "__main__":
    unittest.main()
