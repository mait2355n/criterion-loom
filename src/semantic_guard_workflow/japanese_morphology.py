from __future__ import annotations

"""Optional SudachiPy adapter for Japanese morphological signals.

The adapter deliberately exposes tokens and source offsets only.  A token is
not a dependency edge, semantic relation, or assertion.  SudachiPy and its
dictionary remain optional dependencies and are imported on the first call to
``analyze``.
"""

from importlib import import_module, metadata
from typing import Any, Mapping


class MorphologyError(RuntimeError):
    """Base error for an explicitly requested morphology operation."""


class MorphologyUnavailableError(MorphologyError):
    """Raised when the optional SudachiPy runtime is not installed."""


class MorphologyAnalysisError(MorphologyError):
    """Raised when SudachiPy or its dictionary cannot analyze the text."""


class SudachiMorphologyProvider:
    """Lazily provide source-aligned SudachiPy token signals.

    ``split_mode`` is one of Sudachi's A, B, or C units.  Constructing the
    provider does not import SudachiPy; this keeps the normal semantic-guard
    import path free of the optional dependency.
    """

    provider_id = "sudachipy"

    def __init__(self, split_mode: str = "C") -> None:
        if not isinstance(split_mode, str):
            raise TypeError("split_mode must be a string")
        normalized_mode = split_mode.upper()
        if normalized_mode not in {"A", "B", "C"}:
            raise ValueError("split_mode must be one of A, B, or C")

        self.split_mode = normalized_mode
        self._module: Any | None = None
        self._dictionary: Any | None = None
        self._tokenizer: Any | None = None
        self._runtime_mode: Any | None = None
        self._provider_version: str | None = None
        self._resource_version: str | None = None

    def analyze(self, text: str) -> Mapping[str, object]:
        """Return JSON-compatible token signals aligned to ``text``.

        Provider and dictionary failures remain explicit.  Callers that want
        another extraction route must choose that route themselves rather than
        receiving a silent fallback from this adapter.
        """

        if not isinstance(text, str):
            raise TypeError("text must be a string")

        self._ensure_runtime()
        try:
            morphemes = self._tokenizer.tokenize(text, self._runtime_mode)
            tokens = self._map_tokens(text, morphemes)
        except MorphologyAnalysisError:
            raise
        except Exception as exc:
            raise MorphologyAnalysisError("SudachiPy failed to analyze the supplied text") from exc

        return {
            "provider_id": self.provider_id,
            "provider_version": self._provider_version or "unknown",
            "resource_version": self._resource_version,
            "split_mode": self.split_mode,
            "tokens": tokens,
        }

    def _ensure_runtime(self) -> None:
        if self._tokenizer is not None:
            return

        try:
            module = import_module("sudachipy")
        except ImportError as exc:
            raise MorphologyUnavailableError(
                "SudachiPy is unavailable; install the optional SudachiPy runtime before requesting morphology"
            ) from exc

        try:
            dictionary_type = getattr(module, "Dictionary", None)
            if dictionary_type is None:
                dictionary_namespace = getattr(module, "dictionary")
                dictionary_type = getattr(dictionary_namespace, "Dictionary")

            dictionary_instance = dictionary_type()
            tokenizer_instance = dictionary_instance.create()
            runtime_mode = self._resolve_split_mode(module)
            provider_version = self._read_provider_version(module)
            resource_version = self._read_resource_version()
        except Exception as exc:
            raise MorphologyAnalysisError("SudachiPy dictionary initialization failed") from exc

        self._module = module
        self._dictionary = dictionary_instance
        self._tokenizer = tokenizer_instance
        self._runtime_mode = runtime_mode
        self._provider_version = provider_version
        self._resource_version = resource_version

    def _resolve_split_mode(self, module: Any) -> Any:
        split_mode_type = getattr(module, "SplitMode", None)
        if split_mode_type is None:
            tokenizer_namespace = getattr(module, "tokenizer")
            tokenizer_type = getattr(tokenizer_namespace, "Tokenizer")
            split_mode_type = getattr(tokenizer_type, "SplitMode")
        return getattr(split_mode_type, self.split_mode)

    @staticmethod
    def _read_provider_version(module: Any) -> str:
        module_version = getattr(module, "__version__", None)
        if module_version:
            return str(module_version)
        try:
            return metadata.version("SudachiPy")
        except metadata.PackageNotFoundError:
            return "unknown"

    @staticmethod
    def _read_resource_version() -> str | None:
        # ``Dictionary()`` uses sudachidict_core by default.  Custom dictionary
        # paths are not accepted by this bounded provider, so the distribution
        # version is an adequate reproducibility signal when it is available.
        for distribution in ("SudachiDict-core", "sudachidict_core"):
            try:
                return metadata.version(distribution)
            except metadata.PackageNotFoundError:
                continue
        return None

    @classmethod
    def _map_tokens(cls, text: str, morphemes: Any) -> list[dict[str, object]]:
        tokens: list[dict[str, object]] = []
        cursor = 0
        for morpheme in morphemes:
            surface = cls._surface(morpheme)
            start, end = cls._source_offsets(text, morpheme, surface, cursor)
            cursor = end
            try:
                normalized = str(morpheme.normalized_form())
                lemma = str(morpheme.dictionary_form())
                pos = [str(value) for value in morpheme.part_of_speech()]
            except Exception as exc:
                raise MorphologyAnalysisError("SudachiPy returned an incomplete morpheme") from exc

            tokens.append(
                {
                    "surface": surface,
                    "normalized": normalized,
                    "lemma": lemma,
                    "pos": pos,
                    "start": start,
                    "end": end,
                }
            )
        return tokens

    @staticmethod
    def _surface(morpheme: Any) -> str:
        raw_surface = getattr(morpheme, "raw_surface", None)
        try:
            value = raw_surface() if callable(raw_surface) else morpheme.surface()
        except Exception as exc:
            raise MorphologyAnalysisError("SudachiPy returned a morpheme without a usable surface") from exc
        surface = str(value)
        if not surface:
            raise MorphologyAnalysisError("SudachiPy returned an empty morpheme surface")
        return surface

    @staticmethod
    def _source_offsets(text: str, morpheme: Any, surface: str, cursor: int) -> tuple[int, int]:
        begin = getattr(morpheme, "begin", None)
        finish = getattr(morpheme, "end", None)
        if callable(begin) and callable(finish):
            try:
                start = int(begin())
                end = int(finish())
            except (TypeError, ValueError):
                start = -1
                end = -1
            if start >= cursor and end >= start and text[start:end] == surface:
                return start, end

        # Older or substituted implementations may not expose begin/end.
        # Searching only at or after the prior token keeps repeated surfaces
        # aligned to their respective occurrence in the original text.
        start = text.find(surface, cursor)
        if start < 0:
            raise MorphologyAnalysisError("SudachiPy token surface could not be aligned to the original text")
        return start, start + len(surface)


__all__ = [
    "MorphologyAnalysisError",
    "MorphologyError",
    "MorphologyUnavailableError",
    "SudachiMorphologyProvider",
]
