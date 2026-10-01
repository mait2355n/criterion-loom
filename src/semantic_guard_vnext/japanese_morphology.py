from __future__ import annotations

from importlib import metadata

from .providers import (
    AnalysisAttempt,
    AnalysisSpan,
    ProviderAuthority,
    ProviderRequest,
    TokenCandidate,
)


class SudachiMorphologyProvider:
    """Optional Japanese token provider.

    Tokens are source-aligned challenge material. They do not assert semantic
    relations and do not release holds.
    """

    stage = "morphology"
    provider_id = "sudachipy"
    capabilities = frozenset({"tokenization", "lemma", "part_of_speech"})

    def __init__(self, *, split_mode: str = "C") -> None:
        if split_mode not in {"A", "B", "C"}:
            raise ValueError("split_mode must be A, B, or C")
        self.split_mode = split_mode
        self.provider_version = _distribution_version("SudachiPy")
        self.resource_version = _distribution_version("SudachiDict-core")

    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        from sudachipy import dictionary, tokenizer

        split = {
            "A": tokenizer.Tokenizer.SplitMode.A,
            "B": tokenizer.Tokenizer.SplitMode.B,
            "C": tokenizer.Tokenizer.SplitMode.C,
        }[self.split_mode]
        instance = dictionary.Dictionary().create()
        tokens: list[TokenCandidate] = []
        scopes = request.target_spans or (AnalysisSpan(0, len(request.text), "document"),)

        for morpheme in instance.tokenize(request.text, split):
            start = int(morpheme.begin())
            end = int(morpheme.end())
            if not any(start < span.end and span.start < end for span in scopes):
                continue
            pos = tuple(str(value) for value in morpheme.part_of_speech())
            tokens.append(
                TokenCandidate(
                    surface=morpheme.surface(),
                    lemma=morpheme.dictionary_form(),
                    normalized=morpheme.normalized_form(),
                    part_of_speech=pos,
                    start=start,
                    end=end,
                    features={
                        "reading": morpheme.reading_form(),
                        "split_mode": self.split_mode,
                    },
                )
            )

        return AnalysisAttempt(
            stage="morphology",
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            resource_version=self.resource_version,
            status="ok",
            authority=ProviderAuthority(),
            requested_capabilities=request.requested_capabilities,
            fulfilled_capabilities=tuple(
                capability
                for capability in request.requested_capabilities
                if capability in self.capabilities
            ),
            covered_spans=tuple(scopes),
            tokens=tuple(tokens),
            upstream_usage=("source_text:consumed",),
            diagnostics=(),
        )


def _distribution_version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "unknown"
