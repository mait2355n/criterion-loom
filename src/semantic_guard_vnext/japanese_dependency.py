from __future__ import annotations

from importlib import metadata
from typing import Any, Callable, Iterable

from .providers import (
    AnalysisAttempt,
    AnalysisSpan,
    ProviderAuthority,
    ProviderRequest,
    RelationCandidate,
    ScopeCandidate,
    TokenCandidate,
)


class GinzaDependencyUnavailableError(RuntimeError):
    """Raised when the optional spaCy/GiNZA runtime cannot be loaded."""


class GinzaDependencyProvider:
    """Source-aligned dependency and scope candidates from spaCy/GiNZA.

    The parser is optional and deliberately imported only when ``analyze`` is
    called.  Its output is candidate material: dependency labels are namespaced
    and the provider never asks for support or hold-mutation authority.
    """

    stage = "dependency_parse"
    provider_id = "spacy-ginza"
    capabilities = frozenset(
        {
            "dependency",
            "scope",
            "predicate_argument",
            "polarity_scope",
            "modality_scope",
            "coordination",
        }
    )

    def __init__(
        self,
        *,
        model_name: str = "ja_ginza",
        nlp: Callable[[str], Any] | None = None,
    ) -> None:
        if not model_name.strip():
            raise ValueError("model_name must be a non-empty string")
        self.model_name = model_name
        self._nlp = nlp
        self.provider_version = _distribution_version("spacy")
        self.resource_version = _resource_version(nlp, model_name)

    def analyze(self, request: ProviderRequest) -> AnalysisAttempt:
        nlp = self._nlp if self._nlp is not None else self._load_nlp()
        document = nlp(request.text)
        self.resource_version = _resource_version(nlp, self.model_name)

        covered_spans = request.target_spans or (
            AnalysisSpan(0, len(request.text), "document"),
        )
        document_tokens = tuple(document)
        selected_tokens = tuple(
            token
            for token in document_tokens
            if _overlaps_any(_token_span(token), covered_spans)
        )
        selected_indices = {_token_index(token) for token in selected_tokens}

        tokens = tuple(_token_candidate(token, request.text) for token in selected_tokens)
        relations = tuple(
            relation
            for token in selected_tokens
            if (relation := _dependency_candidate(token, selected_indices)) is not None
        )
        scopes = _scope_candidates(request.text, selected_tokens, covered_spans)

        diagnostics: tuple[str, ...] = ()
        if request.text and not selected_tokens:
            diagnostics = ("no_tokens_in_requested_spans",)

        return AnalysisAttempt(
            stage="dependency_parse",
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
            covered_spans=tuple(covered_spans),
            tokens=tokens,
            relations=relations,
            scopes=scopes,
            upstream_usage=(
                "upstream_tokens:ignored_independent_reparse",
                "source_text:consumed",
            ),
            diagnostics=diagnostics,
        )

    def _load_nlp(self) -> Callable[[str], Any]:
        try:
            import spacy
        except (ImportError, ModuleNotFoundError) as exc:
            raise GinzaDependencyUnavailableError(
                "spaCy/GiNZA dependency analysis is not installed; "
                "install spaCy, GiNZA, and a Japanese model or inject an nlp object"
            ) from exc

        try:
            nlp = spacy.load(self.model_name)
        except Exception as initial_exc:
            # ja_ginza 5.2 was authored for spaCy 3.7.  Newer spaCy releases
            # validate the bundled ``compound_splitter.split_mode = null``
            # more strictly.  Retry with the model's documented A split mode;
            # any other failure remains an explicit provider failure.
            try:
                nlp = spacy.load(
                    self.model_name,
                    config={
                        "components": {
                            "compound_splitter": {"split_mode": "A"}
                        }
                    },
                )
            except Exception as retry_exc:
                raise GinzaDependencyUnavailableError(
                    f"spaCy could not load the GiNZA model {self.model_name!r}; "
                    "install a compatible named model or inject an nlp object; "
                    f"initial_error={type(initial_exc).__name__}; "
                    f"retry_error={type(retry_exc).__name__}"
                ) from retry_exc
        self._nlp = nlp
        self.resource_version = _resource_version(nlp, self.model_name)
        return nlp


def _distribution_version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "unknown"


def _resource_version(nlp: Any, fallback: str) -> str:
    meta = getattr(nlp, "meta", {}) if nlp is not None else {}
    if isinstance(meta, dict):
        name = str(meta.get("name", "")).strip()
        version = str(meta.get("version", "")).strip()
        if name and version:
            return f"{name}:{version}"
        if version:
            return version
    return _distribution_version(fallback) if nlp is None else "unknown"


def _token_span(token: Any) -> AnalysisSpan:
    start = int(token.idx)
    return AnalysisSpan(start, start + len(str(token.text)), "token")


def _token_index(token: Any) -> int:
    return int(getattr(token, "i", token.idx))


def _overlaps(left: AnalysisSpan, right: AnalysisSpan) -> bool:
    return left.start < right.end and right.start < left.end


def _overlaps_any(span: AnalysisSpan, targets: Iterable[AnalysisSpan]) -> bool:
    return any(_overlaps(span, target) for target in targets)


def _token_candidate(token: Any, source: str) -> TokenCandidate:
    span = _token_span(token)
    features = _morph_features(getattr(token, "morph", None))
    ent_type = str(getattr(token, "ent_type_", "")).strip()
    if ent_type:
        features["entity_type"] = ent_type
    dependency = str(getattr(token, "dep_", "")).strip()
    if dependency:
        features["dependency"] = dependency

    surface = source[span.start : span.end]
    lemma = str(getattr(token, "lemma_", "") or surface)
    normalized = str(getattr(token, "norm_", "") or lemma)
    part_of_speech = tuple(
        value
        for value in (
            str(getattr(token, "pos_", "")).strip(),
            str(getattr(token, "tag_", "")).strip(),
        )
        if value
    )
    return TokenCandidate(
        surface=surface,
        lemma=lemma,
        normalized=normalized,
        part_of_speech=part_of_speech,
        start=span.start,
        end=span.end,
        features=features,
    )


def _morph_features(morph: Any) -> dict[str, str]:
    if morph is None:
        return {}
    to_dict = getattr(morph, "to_dict", None)
    if callable(to_dict):
        values = to_dict()
        if isinstance(values, dict):
            return {str(key): str(value) for key, value in values.items()}
    rendered = str(morph).strip()
    return {"morphology": rendered} if rendered else {}


def _dependency_candidate(
    token: Any,
    selected_indices: set[int],
) -> RelationCandidate | None:
    head = getattr(token, "head", None)
    if (
        head is None
        or _token_index(head) == _token_index(token)
        or _token_index(head) not in selected_indices
    ):
        return None
    dependency = str(getattr(token, "dep_", "") or "unknown").strip().lower()
    if dependency == "root":
        return None
    return RelationCandidate(
        relation_kind=f"dependency:{dependency}",
        from_span=_token_span(token),
        to_span=_token_span(head),
        confidence=None,
        interpretation_id=f"dependency:{getattr(token, 'i', token.idx)}:{getattr(head, 'i', head.idx)}",
        rationale="parser_candidate_only",
    )


_NEGATION_FORMS = frozenset({"ない", "無い", "ぬ", "ん", "ず", "ません"})
_CONDITION_FORMS = frozenset(
    {"場合", "とき", "時", "なら", "ならば", "ば", "たら", "れば", "際", "限り"}
)
_MODALITY_FORMS = frozenset(
    {
        "べき",
        "必要",
        "可能",
        "できる",
        "禁止",
        "許可",
        "推奨",
        "想定",
        "予定",
        "はず",
        "だろう",
        "かもしれない",
    }
)
_QUOTE_PAIRS = {"「": "」", "『": "』", "\u201c": "\u201d"}


def _scope_candidates(
    source: str,
    tokens: tuple[Any, ...],
    covered_spans: tuple[AnalysisSpan, ...],
) -> tuple[ScopeCandidate, ...]:
    candidates: list[ScopeCandidate] = []
    for token in tokens:
        surface = str(token.text)
        lemma = str(getattr(token, "lemma_", "") or surface)
        dependency = str(getattr(token, "dep_", "")).lower()
        cue = _token_span(token)
        target = _scope_target(token)
        if dependency == "neg" or surface in _NEGATION_FORMS or lemma in _NEGATION_FORMS:
            candidates.append(ScopeCandidate("negation", cue, target, None))
        if surface in _CONDITION_FORMS or lemma in _CONDITION_FORMS:
            candidates.append(ScopeCandidate("condition", cue, target, None))
        if (
            surface in _MODALITY_FORMS
            or lemma in _MODALITY_FORMS
            or surface.endswith("べき")
            or lemma.endswith("べき")
        ):
            candidates.append(ScopeCandidate("modality", cue, target, None))
        if surface == "と" and dependency in {"case", "mark", "quot", "obl"}:
            candidates.append(ScopeCandidate("quotation", cue, target, None))

    candidates.extend(_quoted_spans(source, covered_spans))
    return _deduplicate_scopes(candidates)


def _scope_target(token: Any) -> AnalysisSpan | None:
    head = getattr(token, "head", None)
    if head is None or _token_index(head) == _token_index(token):
        return None
    return _token_span(head)


def _quoted_spans(
    source: str,
    covered_spans: tuple[AnalysisSpan, ...],
) -> tuple[ScopeCandidate, ...]:
    candidates: list[ScopeCandidate] = []
    for opening, closing in _QUOTE_PAIRS.items():
        search_from = 0
        while True:
            start = source.find(opening, search_from)
            if start < 0:
                break
            end = source.find(closing, start + len(opening))
            if end < 0:
                break
            cue = AnalysisSpan(start, start + len(opening), "quotation_cue")
            target = AnalysisSpan(start + len(opening), end, "quoted_content")
            if target.start < target.end and _overlaps_any(target, covered_spans):
                candidates.append(ScopeCandidate("quotation", cue, target, None))
            search_from = end + len(closing)
    return tuple(candidates)


def _deduplicate_scopes(
    candidates: Iterable[ScopeCandidate],
) -> tuple[ScopeCandidate, ...]:
    unique: dict[
        tuple[str, int, int, int | None, int | None],
        ScopeCandidate,
    ] = {}
    for candidate in candidates:
        target = candidate.target_span
        key = (
            candidate.scope_kind,
            candidate.cue_span.start,
            candidate.cue_span.end,
            target.start if target is not None else None,
            target.end if target is not None else None,
        )
        unique.setdefault(key, candidate)
    return tuple(unique.values())
