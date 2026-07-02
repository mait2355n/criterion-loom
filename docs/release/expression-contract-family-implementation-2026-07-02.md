# Expression Contract Family Implementation 2026-07-02

## Purpose

This note records the first implementation pass for two `doc.expression.*`
contract-family rules promoted from the problem-seeking LLM document audit:

- `doc.expression.capability_contract_missing`
- `doc.expression.mapping_contract_missing`

The goal is recall-oriented document wording detection. This is not a style
lint, a rewrite engine, or a final acceptance decision.

## Implemented Behavior

`doc.expression.capability_contract_missing` warns when broad capability or
completeness wording does not expose enough operational shape:

- scope boundary;
- input boundary;
- limit or non-guarantee;
- evidence or output shape.

Representative warning examples:

```text
資源全体を見渡し、次に何を扱うべきかを決める。
入力から取れる情報をすべて拾わせる。
extract all visible facts before generating every material missing question
```

Representative pass example:

```text
指定された入力から現在の規則で検出できた候補をJSON findingsとして返し、網羅性は保証しない。
```

`doc.expression.mapping_contract_missing` warns when mapping, enrichment,
routing, promotion, or closure wording does not expose enough operational shape:

- source field;
- destination field;
- rule or condition;
- evidence preservation.

Representative warning examples:

```text
監査結果を資源状態、危険、次行動へ写像する。
handoff itemにownerとnext_actionを補って管理対象へ昇格させる。
```

Representative pass example:

```text
findingsとevidenceをaudit_record.fieldsに写し、source_audit_idを保持する。
```

## Calibration Notes

The implementation intentionally uses standard-library string and regular
expression heuristics. It does not add morphological analysis.

The first pass found and fixed obvious over-warning surfaces:

- bare English `every repository` is not treated as a capability claim;
- Japanese compounds such as `全体図` are not treated as broad capability claims;
- negated non-capability prose such as `網羅的な要求検証は担当しない` is not
  treated as a capability overclaim;
- closed-loop wording such as `閉じた制御環` is not treated as a mapping or
  closure contract by itself.

## Verification

Commands run:

```sh
uv run --python 3.13 --project . python -m unittest tests.test_conventions -v
uv run --python 3.13 --project . semantic-guard audit-conventions --kind document --file README.ja.md
uv run --python 3.13 --project . semantic-guard audit-conventions --kind document --file <resource-control-plane>/README.md
uv run --python 3.13 --project . semantic-guard audit-conventions --kind document --file <resource-control-plane>/docs/audit-integration.md
```

Replace `<resource-control-plane>` with the local checkout path when reproducing
the cross-repository smoke checks.

Observed results:

- `tests.test_conventions`: 34 tests passed.
- `README.ja.md`: emits `doc.expression.capability_contract_missing` for the
  LLM exhaustive-extraction wording.
- `resource-control-plane/README.md`: emits
  `doc.expression.capability_contract_missing` and
  `doc.expression.mapping_contract_missing` against the intended control-plane
  wording surfaces.
- `resource-control-plane/docs/audit-integration.md`: emits
  `doc.expression.mapping_contract_missing` for audit-to-control-plane mapping.

## Remaining Work

The next likely contract families are:

- `doc.expression.abstract_material_contract_missing`;
- `doc.expression.evaluation_axis_missing`;
- `doc.expression.acceptance_contract_missing`;
- `doc.expression.closure_contract_missing`.

These should not be added until their trigger terms, required slots, pass
examples, and suppression examples are fixed in tests.
