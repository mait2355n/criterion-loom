# Expression Precision Reference Heuristic 2026-07-01

## Purpose

This note records the implementation boundary for detecting unclear
demonstrative references in document prose.

It is a maintenance handoff, not a release announcement. The public rule is
defined in `docs/conventions/base-contract.json` as
`doc.expression.demonstrative_reference_blurred`.

## Audience And Use

This note is for maintainers changing the expression-precision detector,
fixtures, or convention catalog. Use it to preserve the default heuristic
boundary before adding optional NLP dependencies, LLM review, or broader
reference resolution.

## Decision

Use a standard-library reference heuristic as the default implementation.

Do not make morphological analysis, external NLP packages, or LLM review a
required path for `audit-conventions`.

Reasons:

- demonstrative detection does not require a morphological analyzer;
- morphological analysis can improve noun-phrase boundaries but does not decide
  referent identity by itself;
- dictionary and package dependencies would increase installation and
  distribution risk for a small first-slice gain;
- deterministic warning behavior should remain available in minimal local
  environments.

## Detector Boundary

The detector warns when a demonstrative or vague demonstrative-head phrase is
used and no nearby named referent can be recovered.

Examples that should warn:

```text
それを外部へ出す。
これを判断できる形にする。
この内容を判断できる形にする。
```

Examples that should pass expression precision:

```text
未決定事項を抽出し、その一覧を JSON の findings として返す。
schema_version と status を読み、その値を diagnostics.result に保存する。
要求文を受け取る。
その文書から未決定事項を抽出する。
```

## Candidate Extraction

The default detector uses nearby text only:

- same-line text before the demonstrative;
- up to two previous non-empty lines;
- nearest heading or list parent in local context;
- immediate definition clauses such as `これは X である`;
- code spans and ASCII identifiers;
- Japanese noun phrases around particles such as `を`, `は`, `が`, `に`,
  `として`;
- schema, record, artifact, field, finding, diagnostic, and manifest terms.

Candidate strength:

- `strong`: code spans, ASCII identifiers, schema fields, manifest fields, and
  explicit field-like terms;
- `medium`: one recoverable Japanese noun phrase or support term;
- `weak` candidate label: broad carrier noun tokens, for example Japanese
  terms meaning content, thing, part, place, material, target, result, or value.

Decision:

- pass when a strong candidate exists;
- pass when exactly one medium candidate exists;
- warn when no candidate exists;
- warn when only weak candidates exist;
- warn when multiple medium candidates exist and no strong candidate is
  present.

## Expected Effect

Expected local value:

- high recall for short unclear Japanese demonstrative-reference tokens;
- lower false positives for same-sentence anchored phrases such as `その一覧`;
- better review evidence because candidate extraction is reported under
  `details.expression_precision.referent_resolutions`.

Known limits:

- long-distance reference is not solved;
- conceptual references across paragraphs remain residual risk;
- corpus precision is not guaranteed by unit tests;
- the warning is document-revision material, not final acceptance or rejection.

## Morphological Analysis Gate

Morphological analysis may be reconsidered only after a corpus sweep shows that
the default heuristic is insufficient.

Suggested gate:

- false positives exceed roughly 30% on a labeled local demonstrative-reference
  set;
- false negatives are mainly caused by noun-phrase boundary errors rather than
  semantic interpretation;
- an optional analyzer improves borderline-case accuracy by roughly 20
  percentage points or more;
- the package and dictionary cost is acceptable for the target distribution.

If added, it should be optional, for example as a future extra such as
`semantic-guard[nlp]`, with fallback to the standard-library detector.

## Verification Scope

Minimum checks after changing this detector:

```sh
uv run --python 3.13 --project . python -m json.tool docs/conventions/base-contract.json
uv run --python 3.13 --project . python -m unittest tests.test_conventions -v
uv run --python 3.13 --project . python -m unittest discover -s tests -v
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
uv run --python 3.13 --project . semantic-guard audit-conventions --kind document --text "それを外部へ出す。"
uv run --python 3.13 --project . semantic-guard audit-conventions --kind document --text "未決定事項を抽出し、その一覧を JSON の findings として返す。"
uv run --python 3.13 --project . semantic-guard finish-check --text "tests_ran: ..."
```
