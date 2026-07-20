from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Iterable

from .providers import AnalysisAttempt, AnalysisSpan, ProviderRequest


RECEIPT_SCHEMA_VERSION = "semantic-guard-provider-execution-receipt/v0"
QUALIFICATION_SCHEMA_VERSION = "semantic-guard-analyzer-qualification/v0"


def _wire(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _wire(asdict(value))
    if isinstance(value, dict):
        return {str(key): _wire(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_wire(item) for item in value]
    return value


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        _wire(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def source_digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _spans(value: Iterable[AnalysisSpan]) -> tuple[tuple[int, int, str], ...]:
    return tuple((item.start, item.end, item.role) for item in value)


def _request_material(request: ProviderRequest) -> dict[str, Any]:
    return {
        "source_digest": source_digest(request.text),
        "target_spans": _spans(request.target_spans),
        "reason_codes": request.reason_codes,
        "requested_capabilities": request.requested_capabilities,
        "upstream_tokens": request.upstream_tokens,
        "upstream_relations": request.upstream_relations,
        "upstream_scopes": request.upstream_scopes,
    }


def _upstream_material(request: ProviderRequest) -> dict[str, Any]:
    return {
        "tokens": request.upstream_tokens,
        "relations": request.upstream_relations,
        "scopes": request.upstream_scopes,
    }


def _output_material(attempt: AnalysisAttempt) -> dict[str, Any]:
    return {
        "stage": attempt.stage,
        "provider_id": attempt.provider_id,
        "provider_version": attempt.provider_version,
        "resource_version": attempt.resource_version,
        "status": attempt.status,
        "authority": attempt.authority,
        "requested_capabilities": attempt.requested_capabilities,
        "fulfilled_capabilities": attempt.fulfilled_capabilities,
        "covered_spans": attempt.covered_spans,
        "tokens": attempt.tokens,
        "relations": attempt.relations,
        "scopes": attempt.scopes,
        "upstream_usage": attempt.upstream_usage,
        "diagnostics": attempt.diagnostics,
    }


@dataclass(frozen=True, slots=True)
class ProviderExecutionReceipt:
    source_digest: str
    request_digest: str
    output_digest: str
    provider_id: str
    provider_version: str
    resource_version: str
    stage: str
    status: str
    target_spans: tuple[AnalysisSpan, ...]
    covered_spans: tuple[AnalysisSpan, ...]
    requested_capabilities: tuple[str, ...]
    fulfilled_capabilities: tuple[str, ...]
    upstream_digest: str
    upstream_usage: tuple[str, ...]
    receipt_id: str = field(init=False)
    schema_version: str = field(init=False, default=RECEIPT_SCHEMA_VERSION)

    def __post_init__(self) -> None:
        for name in (
            "source_digest",
            "request_digest",
            "output_digest",
            "provider_id",
            "stage",
            "status",
            "upstream_digest",
        ):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be a non-empty string")
        material = {
            "schema_version": self.schema_version,
            "source_digest": self.source_digest,
            "request_digest": self.request_digest,
            "output_digest": self.output_digest,
            "provider": (
                self.provider_id,
                self.provider_version,
                self.resource_version,
            ),
            "stage": self.stage,
            "status": self.status,
            "target_spans": _spans(self.target_spans),
            "covered_spans": _spans(self.covered_spans),
            "requested_capabilities": self.requested_capabilities,
            "fulfilled_capabilities": self.fulfilled_capabilities,
            "upstream_digest": self.upstream_digest,
            "upstream_usage": self.upstream_usage,
        }
        object.__setattr__(self, "receipt_id", "receipt." + canonical_digest(material)[7:])

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "source_digest": self.source_digest,
            "request_digest": self.request_digest,
            "output_digest": self.output_digest,
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "resource_version": self.resource_version,
            "stage": self.stage,
            "status": self.status,
            "target_spans": [
                {"start": item.start, "end": item.end, "role": item.role}
                for item in self.target_spans
            ],
            "covered_spans": [
                {"start": item.start, "end": item.end, "role": item.role}
                for item in self.covered_spans
            ],
            "requested_capabilities": list(self.requested_capabilities),
            "fulfilled_capabilities": list(self.fulfilled_capabilities),
            "upstream_digest": self.upstream_digest,
            "upstream_usage": list(self.upstream_usage),
        }


def build_provider_execution_receipt(
    request: ProviderRequest,
    attempt: AnalysisAttempt,
) -> ProviderExecutionReceipt:
    """Create an engine-owned receipt over the sanitized provider boundary."""

    return ProviderExecutionReceipt(
        source_digest=source_digest(request.text),
        request_digest=canonical_digest(_request_material(request)),
        output_digest=canonical_digest(_output_material(attempt)),
        provider_id=attempt.provider_id,
        provider_version=attempt.provider_version,
        resource_version=attempt.resource_version,
        stage=attempt.stage,
        status=attempt.status,
        target_spans=tuple(request.target_spans),
        covered_spans=tuple(attempt.covered_spans),
        requested_capabilities=tuple(attempt.requested_capabilities),
        fulfilled_capabilities=tuple(attempt.fulfilled_capabilities),
        upstream_digest=canonical_digest(_upstream_material(request)),
        upstream_usage=tuple(attempt.upstream_usage),
    )


def attempt_output_digest(attempt: AnalysisAttempt) -> str:
    return canonical_digest(_output_material(attempt))


@dataclass(frozen=True, slots=True)
class AnalyzerQualification:
    provider_id: str
    provider_version: str
    resource_version: str
    capabilities: tuple[str, ...]
    policy_scope: str
    qualification_basis: str
    qualification_id: str = field(init=False)
    schema_version: str = field(init=False, default=QUALIFICATION_SCHEMA_VERSION)

    def __post_init__(self) -> None:
        for name in (
            "provider_id",
            "provider_version",
            "resource_version",
            "policy_scope",
            "qualification_basis",
        ):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be a non-empty string")
        raw_capabilities = tuple(self.capabilities)
        if (
            not raw_capabilities
            or any(not isinstance(item, str) or not item.strip() for item in raw_capabilities)
            or len(set(raw_capabilities)) != len(raw_capabilities)
        ):
            raise ValueError("capabilities must contain non-empty unique values")
        capabilities = tuple(sorted(raw_capabilities))
        object.__setattr__(self, "capabilities", capabilities)
        material = {
            "schema_version": self.schema_version,
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "resource_version": self.resource_version,
            "capabilities": self.capabilities,
            "policy_scope": self.policy_scope,
            "qualification_basis": self.qualification_basis,
        }
        object.__setattr__(
            self,
            "qualification_id",
            "qualification." + canonical_digest(material)[7:],
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "qualification_id": self.qualification_id,
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "resource_version": self.resource_version,
            "capabilities": list(self.capabilities),
            "policy_scope": self.policy_scope,
            "qualification_basis": self.qualification_basis,
        }


@dataclass(frozen=True, slots=True)
class QualifiedAnalyzerRegistry:
    """Trusted, exact-match qualification registry; empty by default."""

    records: tuple[AnalyzerQualification, ...] = ()

    def __post_init__(self) -> None:
        records = tuple(self.records)
        if len({item.qualification_id for item in records}) != len(records):
            raise ValueError("qualification records must be unique")
        object.__setattr__(self, "records", records)

    def match(
        self,
        receipt: ProviderExecutionReceipt,
        *,
        required_capabilities: tuple[str, ...],
        policy_scope: str,
    ) -> AnalyzerQualification | None:
        required = set(required_capabilities)
        matches = tuple(
            item
            for item in self.records
            if item.provider_id == receipt.provider_id
            and item.provider_version == receipt.provider_version
            and item.resource_version == receipt.resource_version
            and item.policy_scope == policy_scope
            and set(item.capabilities) == required
        )
        return matches[0] if len(matches) == 1 else None


EMPTY_QUALIFIED_ANALYZER_REGISTRY = QualifiedAnalyzerRegistry()


__all__ = [
    "AnalyzerQualification",
    "EMPTY_QUALIFIED_ANALYZER_REGISTRY",
    "ProviderExecutionReceipt",
    "QualifiedAnalyzerRegistry",
    "build_provider_execution_receipt",
    "attempt_output_digest",
    "canonical_digest",
    "source_digest",
]
