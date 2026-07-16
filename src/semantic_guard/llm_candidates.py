from __future__ import annotations

import hashlib
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker

from .providers import (
    AnalysisAttempt,
    AnalysisSpan,
    ProviderAuthority,
    ProviderRequest,
    RelationCandidate,
    ScopeCandidate,
)
from .public_contract import load_public_schema


class SubmittedLLMCandidateProvider:
    """Turn a closed, digest-bound caller submission into candidate material.

    The submitting caller may itself be a coding agent backed by an LLM.  The
    recorded model and prompt profile are provenance claims, not authenticated
    identity.  Runtime authority remains candidate-only regardless of those
    claims.
    """

    stage = "llm_candidate"
    capabilities = frozenset(
        {"interpretation_candidates", "countercondition_candidates"}
    )

    def __init__(self, bundle: Mapping[str, Any]) -> None:
        material = dict(bundle)
        Draft202012Validator(
            load_public_schema("llm-candidate-input"),
            format_checker=FormatChecker(),
        ).validate(material)
        self._bundle = material
        self.provider_id = f"submitted-llm:{material['model_id']}"
        self.provider_version = str(material["model_version"])
        self.resource_version = (
            f"{material['prompt_profile_id']}:{material['prompt_profile_version']}"
        )

    @property
    def bundle_id(self) -> str:
        return str(self._bundle["bundle_id"])

    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        expected = hashlib.sha256(request.text.encode("utf-8")).hexdigest()
        observed = str(self._bundle["source_digest"]["value"])
        if observed != expected:
            raise ValueError(
                f"llm_candidate_source_digest_mismatch:{observed}:{expected}"
            )
        relations = tuple(
            RelationCandidate(
                relation_kind=str(item["relation_kind"]),
                from_span=_span(item["from_span"]),
                to_span=_span(item["to_span"]),
                confidence=item.get("confidence"),
                interpretation_id=str(item["interpretation_id"]),
                rationale=str(item["rationale"]),
            )
            for item in self._bundle["relations"]
        )
        scopes = tuple(
            ScopeCandidate(
                scope_kind=str(item["scope_kind"]),
                cue_span=_span(item["cue_span"]),
                target_span=(
                    _span(item["target_span"])
                    if item["target_span"] is not None
                    else None
                ),
                confidence=item.get("confidence"),
            )
            for item in self._bundle["scopes"]
        )
        return AnalysisAttempt(
            stage="llm_candidate",
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            resource_version=self.resource_version,
            status="ok",
            authority=ProviderAuthority(
                support=False,
                challenge_signal=True,
                apply_hold=False,
                release_hold=False,
            ),
            requested_capabilities=request.requested_capabilities,
            fulfilled_capabilities=tuple(
                capability
                for capability in request.requested_capabilities
                if capability in self.capabilities
            ),
            covered_spans=request.target_spans,
            relations=relations,
            scopes=scopes,
            upstream_usage=("upstream_context:ignored_closed_submission",),
            diagnostics=(
                f"submitted_bundle:{self.bundle_id}",
                *tuple(str(item) for item in self._bundle["diagnostics"]),
            ),
        )


def _span(value: Mapping[str, Any]) -> AnalysisSpan:
    return AnalysisSpan(
        start=int(value["start"]),
        end=int(value["end"]),
        role=str(value["role"]),
    )


__all__ = ["SubmittedLLMCandidateProvider"]
