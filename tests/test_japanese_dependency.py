from __future__ import annotations

import sys
import unittest
from unittest.mock import patch

from semantic_guard.japanese_dependency import (
    GinzaDependencyProvider,
    GinzaDependencyUnavailableError,
)
from semantic_guard.providers import AnalysisSpan, ProviderRequest, run_provider


class FakeMorph:
    def __init__(self, **values: str) -> None:
        self.values = values

    def to_dict(self) -> dict[str, str]:
        return dict(self.values)


class FakeToken:
    def __init__(
        self,
        text: str,
        idx: int,
        i: int,
        *,
        lemma: str | None = None,
        dependency: str,
        pos: str = "NOUN",
    ) -> None:
        self.text = text
        self.idx = idx
        self.i = i
        self.lemma_ = lemma or text
        self.norm_ = lemma or text
        self.dep_ = dependency
        self.pos_ = pos
        self.tag_ = pos
        self.ent_type_ = ""
        self.morph = FakeMorph(Reading=text)
        self.head: FakeToken = self


class FakeNlp:
    meta = {"name": "fake_ginza", "version": "1.2.3"}

    def __init__(self, tokens: tuple[FakeToken, ...]) -> None:
        self.tokens = tokens

    def __call__(self, text: str) -> tuple[FakeToken, ...]:
        return self.tokens


def _tokens_for(text: str) -> tuple[FakeToken, ...]:
    surfaces = ("「", "実行", "する", "」", "と", "報告", "すべき", "で", "ない", "場合")
    tokens: list[FakeToken] = []
    offset = 0
    dependencies = ("punct", "obj", "aux", "punct", "case", "ROOT", "aux", "aux", "neg", "mark")
    poses = ("PUNCT", "NOUN", "AUX", "PUNCT", "ADP", "VERB", "AUX", "AUX", "AUX", "NOUN")
    for index, (surface, dependency, pos) in enumerate(zip(surfaces, dependencies, poses)):
        start = text.index(surface, offset)
        tokens.append(
            FakeToken(
                surface,
                start,
                index,
                dependency=dependency,
                pos=pos,
            )
        )
        offset = start + len(surface)

    root = tokens[5]
    for token in tokens:
        token.head = root
    root.head = root
    tokens[8].head = tokens[1]
    tokens[9].head = root
    return tuple(tokens)


class GinzaDependencyProviderTests(unittest.TestCase):
    def test_fake_model_preserves_offsets_and_emits_candidate_only_analysis(self) -> None:
        text = "「実行する」と報告すべきでない場合"
        provider = GinzaDependencyProvider(nlp=FakeNlp(_tokens_for(text)))
        request = ProviderRequest(
            text=text,
            target_spans=(AnalysisSpan(0, len(text), "requirement"),),
            reason_codes=("attachment_unknown",),
            requested_capabilities=("dependency", "scope"),
        )

        attempt = run_provider(provider, request, stage="dependency_parse")

        self.assertEqual(attempt.status, "ok")
        self.assertEqual(attempt.stage, "dependency_parse")
        self.assertEqual(attempt.resource_version, "fake_ginza:1.2.3")
        self.assertEqual(attempt.covered_spans, request.target_spans)
        self.assertEqual(attempt.fulfilled_capabilities, ("dependency", "scope"))
        self.assertFalse(attempt.authority.support)
        self.assertTrue(attempt.authority.challenge_signal)
        self.assertFalse(attempt.authority.apply_hold)
        self.assertFalse(attempt.authority.release_hold)

        for token in attempt.tokens:
            self.assertEqual(token.surface, text[token.start : token.end])
        self.assertTrue(attempt.relations)
        self.assertTrue(
            all(relation.relation_kind.startswith("dependency:") for relation in attempt.relations)
        )
        self.assertFalse(
            {"acts_on", "verified_by", "produces"}
            & {relation.relation_kind for relation in attempt.relations}
        )
        self.assertEqual(
            {"negation", "condition", "quotation", "modality"},
            {scope.scope_kind for scope in attempt.scopes},
        )
        for scope in attempt.scopes:
            self.assertLess(scope.cue_span.start, scope.cue_span.end)
            self.assertLessEqual(scope.cue_span.end, len(text))
            if scope.target_span is not None:
                self.assertLess(scope.target_span.start, scope.target_span.end)
                self.assertLessEqual(scope.target_span.end, len(text))
        quoted_contents = {
            text[scope.target_span.start : scope.target_span.end]
            for scope in attempt.scopes
            if scope.scope_kind == "quotation" and scope.target_span is not None
        }
        self.assertIn("実行する", quoted_contents)

    def test_unimplemented_coreference_capability_is_explicitly_partial(self) -> None:
        text = "「実行する」と報告すべきでない場合"
        provider = GinzaDependencyProvider(nlp=FakeNlp(_tokens_for(text)))
        request = ProviderRequest(
            text=text,
            target_spans=(AnalysisSpan(0, len(text), "requirement"),),
            reason_codes=("attachment_unknown",),
            requested_capabilities=(
                "dependency",
                "predicate_argument",
                "polarity_scope",
                "modality_scope",
                "coordination",
                "coreference_candidate",
            ),
        )

        attempt = run_provider(provider, request, stage="dependency_parse")

        self.assertEqual(attempt.status, "partial")
        self.assertEqual(
            attempt.missing_capabilities,
            ("coreference_candidate",),
        )
        self.assertIn(
            "provider_capabilities_unfulfilled:coreference_candidate",
            attempt.diagnostics,
        )

    def test_target_span_filters_tokens_and_dependency_edges(self) -> None:
        text = "「実行する」と報告すべきでない場合"
        tokens = _tokens_for(text)
        start = text.index("実行")
        end = start + len("実行")
        provider = GinzaDependencyProvider(nlp=FakeNlp(tokens))
        request = ProviderRequest(
            text=text,
            target_spans=(AnalysisSpan(start, end, "unresolved"),),
            reason_codes=("attachment_unknown",),
            requested_capabilities=("dependency",),
        )

        attempt = provider.analyze(request)

        self.assertEqual([token.surface for token in attempt.tokens], ["実行"])
        self.assertEqual(attempt.relations, ())
        self.assertTrue(all(start <= token.start < token.end <= end for token in attempt.tokens))

    def test_missing_optional_runtime_raises_explicit_exception_on_analyze(self) -> None:
        provider = GinzaDependencyProvider()
        request = ProviderRequest(
            text="要求",
            target_spans=(AnalysisSpan(0, 2, "document"),),
            reason_codes=("dependency_required",),
            requested_capabilities=("dependency",),
        )

        with patch.dict(sys.modules, {"spacy": None}):
            with self.assertRaisesRegex(
                GinzaDependencyUnavailableError,
                "spaCy/GiNZA dependency analysis is not installed",
            ):
                provider.analyze(request)


if __name__ == "__main__":
    unittest.main()
