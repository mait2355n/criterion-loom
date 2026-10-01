from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from semantic_guard_workflow.japanese_morphology import (
    MorphologyAnalysisError,
    MorphologyUnavailableError,
    SudachiMorphologyProvider,
)


class _FakeMorpheme:
    def __init__(
        self,
        surface: str,
        *,
        normalized: str | None = None,
        lemma: str | None = None,
        pos: tuple[str, ...] = ("名詞", "普通名詞", "一般", "*", "*", "*"),
    ) -> None:
        self._surface = surface
        self._normalized = normalized or surface
        self._lemma = lemma or self._normalized
        self._pos = pos

    def surface(self) -> str:
        return self._surface

    def normalized_form(self) -> str:
        return self._normalized

    def dictionary_form(self) -> str:
        return self._lemma

    def part_of_speech(self) -> tuple[str, ...]:
        return self._pos


class _OffsetMorpheme(_FakeMorpheme):
    def __init__(self, raw_surface: str, projected_surface: str, start: int, end: int) -> None:
        super().__init__(projected_surface, normalized=projected_surface, lemma=projected_surface)
        self._raw_surface = raw_surface
        self._start = start
        self._end = end

    def raw_surface(self) -> str:
        return self._raw_surface

    def begin(self) -> int:
        return self._start

    def end(self) -> int:
        return self._end


def _fake_sudachi_module(
    tokens: list[_FakeMorpheme] | None = None,
    *,
    analysis_error: Exception | None = None,
    dictionary_error: Exception | None = None,
) -> tuple[SimpleNamespace, dict[str, object]]:
    state: dict[str, object] = {"dictionary_count": 0, "tokenize_calls": []}

    class SplitMode:
        A = "mode-a"
        B = "mode-b"
        C = "mode-c"

    class Tokenizer:
        def tokenize(self, text: str, mode: object) -> list[_FakeMorpheme]:
            calls = state["tokenize_calls"]
            assert isinstance(calls, list)
            calls.append((text, mode))
            if analysis_error is not None:
                raise analysis_error
            return list(tokens or [])

    class Dictionary:
        def __init__(self) -> None:
            state["dictionary_count"] = int(state["dictionary_count"]) + 1
            if dictionary_error is not None:
                raise dictionary_error

        def create(self) -> Tokenizer:
            return Tokenizer()

    return (
        SimpleNamespace(Dictionary=Dictionary, SplitMode=SplitMode, __version__="0.fake"),
        state,
    )


class SudachiMorphologyProviderTests(unittest.TestCase):
    def test_constructor_is_lazy_and_missing_dependency_is_explicit(self) -> None:
        with patch(
            "semantic_guard_workflow.japanese_morphology.import_module",
            side_effect=ModuleNotFoundError("No module named 'sudachipy'"),
        ) as importer:
            provider = SudachiMorphologyProvider()

            importer.assert_not_called()
            with self.assertRaises(MorphologyUnavailableError):
                provider.analyze("要件")
            importer.assert_called_once_with("sudachipy")

    def test_maps_tokens_and_aligns_repeated_surfaces_in_source_order(self) -> None:
        module, state = _fake_sudachi_module(
            [
                _FakeMorpheme("要件", normalized="要件", lemma="要件"),
                _FakeMorpheme("を", pos=("助詞", "格助詞", "*", "*", "*", "*")),
                _FakeMorpheme("要件", normalized="要件", lemma="要件"),
            ]
        )
        with (
            patch("semantic_guard_workflow.japanese_morphology.import_module", return_value=module),
            patch("semantic_guard_workflow.japanese_morphology.metadata.version", return_value="2026.01"),
        ):
            result = SudachiMorphologyProvider(split_mode="b").analyze("要件を要件")

        self.assertEqual(result["provider_id"], "sudachipy")
        self.assertEqual(result["provider_version"], "0.fake")
        self.assertEqual(result["resource_version"], "2026.01")
        self.assertEqual(result["split_mode"], "B")
        self.assertEqual(state["dictionary_count"], 1)
        self.assertEqual(state["tokenize_calls"], [("要件を要件", "mode-b")])
        self.assertEqual(
            result["tokens"],
            [
                {
                    "surface": "要件",
                    "normalized": "要件",
                    "lemma": "要件",
                    "pos": ["名詞", "普通名詞", "一般", "*", "*", "*"],
                    "start": 0,
                    "end": 2,
                },
                {
                    "surface": "を",
                    "normalized": "を",
                    "lemma": "を",
                    "pos": ["助詞", "格助詞", "*", "*", "*", "*"],
                    "start": 2,
                    "end": 3,
                },
                {
                    "surface": "要件",
                    "normalized": "要件",
                    "lemma": "要件",
                    "pos": ["名詞", "普通名詞", "一般", "*", "*", "*"],
                    "start": 3,
                    "end": 5,
                },
            ],
        )
        self.assertNotIn("relations", result)

    def test_uses_raw_surface_and_sudachi_offsets_for_projected_tokens(self) -> None:
        module, _ = _fake_sudachi_module([_OffsetMorpheme("附属", "付属", 0, 2)])
        with (
            patch("semantic_guard_workflow.japanese_morphology.import_module", return_value=module),
            patch("semantic_guard_workflow.japanese_morphology.metadata.version", return_value="2026.01"),
        ):
            result = SudachiMorphologyProvider().analyze("附属")

        self.assertEqual(
            result["tokens"],
            [
                {
                    "surface": "附属",
                    "normalized": "付属",
                    "lemma": "付属",
                    "pos": ["名詞", "普通名詞", "一般", "*", "*", "*"],
                    "start": 0,
                    "end": 2,
                }
            ],
        )

    def test_empty_text_returns_an_empty_token_list(self) -> None:
        module, state = _fake_sudachi_module([])
        with (
            patch("semantic_guard_workflow.japanese_morphology.import_module", return_value=module),
            patch("semantic_guard_workflow.japanese_morphology.metadata.version", return_value="2026.01"),
        ):
            result = SudachiMorphologyProvider().analyze("")

        self.assertEqual(result["tokens"], [])
        self.assertEqual(state["tokenize_calls"], [("", "mode-c")])

    def test_dictionary_failure_is_an_analysis_error(self) -> None:
        module, _ = _fake_sudachi_module(dictionary_error=RuntimeError("dictionary missing"))
        with patch("semantic_guard_workflow.japanese_morphology.import_module", return_value=module):
            with self.assertRaises(MorphologyAnalysisError) as captured:
                SudachiMorphologyProvider().analyze("要件")

        self.assertIsInstance(captured.exception.__cause__, RuntimeError)

    def test_tokenizer_failure_is_an_analysis_error_without_fallback(self) -> None:
        module, _ = _fake_sudachi_module(analysis_error=RuntimeError("analysis failed"))
        with (
            patch("semantic_guard_workflow.japanese_morphology.import_module", return_value=module),
            patch("semantic_guard_workflow.japanese_morphology.metadata.version", return_value="2026.01"),
        ):
            with self.assertRaises(MorphologyAnalysisError) as captured:
                SudachiMorphologyProvider().analyze("要件")

        self.assertIsInstance(captured.exception.__cause__, RuntimeError)

    def test_unalignable_surface_is_an_analysis_error(self) -> None:
        module, _ = _fake_sudachi_module([_FakeMorpheme("不存在")])
        with (
            patch("semantic_guard_workflow.japanese_morphology.import_module", return_value=module),
            patch("semantic_guard_workflow.japanese_morphology.metadata.version", return_value="2026.01"),
        ):
            with self.assertRaises(MorphologyAnalysisError):
                SudachiMorphologyProvider().analyze("要件")

    def test_rejects_an_unknown_split_mode_before_loading_sudachi(self) -> None:
        with patch("semantic_guard_workflow.japanese_morphology.import_module") as importer:
            with self.assertRaises(ValueError):
                SudachiMorphologyProvider("D")
            importer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
