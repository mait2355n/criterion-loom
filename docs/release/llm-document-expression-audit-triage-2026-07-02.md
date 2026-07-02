# LLM Document Expression Audit Triage 2026-07-02

This table is a working triage surface for local raw audit output retained
outside the public tree.

`recommendation` is a Codex recommendation only. Human decision remains pending.

| ID | Resource | Path | Lines | Recommendation | Deterministic visibility | Issue kind | Span |
| --- | --- | --- | ---: | --- | --- | --- | --- |
| `llm-doc-audit.sg-readme.001` | `semantic-guard` | `README.md` | 10 | `detector_gap` | `not_emitted` | `capability_scope_overclaim` | `whether an LLM exploration pass can extract all visible information before asking every material missing question` |
| `llm-doc-audit.sg-readme.002` | `semantic-guard` | `README.md` | 35 | `needs_context` | `not_emitted` | `abstract_output_surface_missing` | `making missing assumptions visible` |
| `llm-doc-audit.sg-readme.003` | `semantic-guard` | `README.md` | 142 | `detector_gap` | `not_emitted` | `capability_scope_overclaim` | `extract all visible facts, inferences, hypotheses, unknowns, and pending human decisions before generating every material missing question` |
| `llm-doc-audit.sg-readme.004` | `semantic-guard` | `README.md` | 415 | `accept_issue` | `not_emitted` | `environment_claim_evidence_missing` | `--execute starts codex exec with an ephemeral read-only sandbox...` |
| `llm-doc-audit.sg-readme.005` | `semantic-guard` | `README.md` | 430-445 | `accept_issue` | `not_emitted` | `routing_threshold_contract_missing` | `review-if-needed detects deterministic audit uncertainty...` |
| `llm-doc-audit.sg-ja.001` | `semantic-guard` | `README.ja.md` | 7 | `accept_issue` | `not_emitted` | `abstract_output_surface_missing` | abstract output-surface wording in an older README draft |
| `llm-doc-audit.sg-ja.002` | `semantic-guard` | `README.ja.md` | 26 | `detector_gap` | `not_emitted` | `capability_scope_overclaim` | `入力と文脈から取れる情報をすべて拾わせた上で...` |
| `llm-doc-audit.sg-ja.003` | `semantic-guard` | `README.ja.md` | 33 | `accept_rewrite_only` | `not_emitted` | `abstract_material_contract_missing` | `fresh-eyes査読を補助材料として挟むかの確認` |
| `llm-doc-audit.sg-ja.004` | `semantic-guard` | `README.ja.md` | 140-155 | `accept_issue` | `emitted_relevant` | `viewpoint_operation_blurred` | deleted company-facing and GitHub-viewing sections from an older README draft |
| `llm-doc-audit.sg-conv-readme.001` | `semantic-guard` | `docs/conventions/README.md` | 6-9 | `accept_rewrite_only` | `not_emitted` | `capability_evidence_missing` | `interoperate without guessing` |
| `llm-doc-audit.sg-conv-readme.002` | `semantic-guard` | `docs/conventions/README.md` | 56-70 | `false_positive_guard` | `emitted_false_positive` | `example_context_false_positive` | `example expressions inside the rule explanation` |
| `llm-doc-audit.sg-base.001` | `semantic-guard` | `docs/conventions/base-contract.md` | 181-185 | `accept_issue` | `not_emitted` | `evaluation_axis_missing` | `until corpus evidence shows ... too much false positive or false negative noise` |
| `llm-doc-audit.sg-base.002` | `semantic-guard` | `docs/conventions/base-contract.md` | 237-250 | `accept_rewrite_only` | `not_emitted` | `precedence_condition_missing` | `The base contract wins only where a repository profile is absent or silent.` |
| `llm-doc-audit.cc-readme.001` | `continuity-concentrator` | `README.md` | 3 | `accept_issue` | `not_emitted` | `abstract_quality_threshold_missing` | `次の作業へ投入できる濃度へ整える` |
| `llm-doc-audit.cc-readme.002` | `continuity-concentrator` | `README.md` | 9 | `accept_issue` | `not_emitted` | `abstract_material_contract_missing` | `文脈材を収集、濃縮、束化し、未解決の残りを露出する` |
| `llm-doc-audit.cc-readme.003` | `continuity-concentrator` | `README.md` | 5 | `false_positive_guard` | `emitted_false_positive` | `demonstrative_reference_false_positive` | `これは監査システムでも管理システムでもない。` |
| `llm-doc-audit.cc-readme.004` | `continuity-concentrator` | `README.md` | 77 | `accept_issue` | `not_emitted` | `evaluation_axis_missing` | `explicit incompleteness over confident reconstruction` |
| `llm-doc-audit.cc-readme.005` | `continuity-concentrator` | `README.md` | 113-114 | `accept_issue` | `not_emitted` | `routing_condition_missing` | `detail_refs escalation refs instead of a default reading list` |
| `llm-doc-audit.rcp-readme.001` | `resource-control-plane` | `README.md` | 3 | `accept_issue` | `not_emitted` | `capability_scope_overclaim` | `資源全体を見渡し、監査結果を取り込み、次に何を扱うべきかを決める` |
| `llm-doc-audit.rcp-readme.002` | `resource-control-plane` | `README.md` | 9-11 | `accept_issue` | `not_emitted` | `abstract_management_target_missing` | `手戻り、誤り候補、証拠不足、根拠喪失を管理対象として扱えるようにする` |
| `llm-doc-audit.rcp-readme.003` | `resource-control-plane` | `README.md` | 17-22 | `accept_rewrite_only` | `emitted_relevant` | `concept_mapping_contract_missing` | `ハーネス工学とオーケストレーションに近い` |
| `llm-doc-audit.rcp-readme.004` | `resource-control-plane` | `README.md` | 24-28 | `accept_issue` | `not_emitted` | `priority_decision_contract_missing` | `何を先に扱うべきか、誰が判断すべきか、どの根拠で閉じるべきか` |
| `llm-doc-audit.rcp-readme.005` | `resource-control-plane` | `README.md` | 136-149 | `accept_issue` | `not_emitted` | `acceptance_evidence_missing` | `見える、設計できる、記録できる、扱える、辿れる` |
| `llm-doc-audit.rcp-audit.001` | `resource-control-plane` | `docs/audit-integration.md` | 5-7 | `accept_issue` | `emitted_relevant` | `viewpoint_operation_blurred` | `監査結果を「判断材料」として扱う` |
| `llm-doc-audit.rcp-audit.002` | `resource-control-plane` | `docs/audit-integration.md` | 36-41 | `accept_issue` | `not_emitted` | `mapping_contract_missing` | `監査結果を資源状態、危険、次行動へ写像する` |
| `llm-doc-audit.rcp-audit.003` | `resource-control-plane` | `docs/audit-integration.md` | 45-47 | `accept_issue` | `emitted_relevant` | `future_contract_boundary_missing` | `まだ実装済みschemaではない / 版付き構造として扱う` |
| `llm-doc-audit.rcp-audit.004` | `resource-control-plane` | `docs/audit-integration.md` | 155-157 | `accept_issue` | `not_emitted` | `handoff_enrichment_contract_missing` | `owner、needed_for、blocking_status、next_action、review_atを補って管理対象へ昇格` |
| `llm-doc-audit.rcp-unresolved.001` | `resource-control-plane` | `docs/unresolved-decision-management.md` | 47 | `accept_rewrite_only` | `not_emitted` | `evaluation_axis_missing` | `未決定は悪ではない。隠れた未決定が悪い。` |
| `llm-doc-audit.rcp-unresolved.002` | `resource-control-plane` | `docs/unresolved-decision-management.md` | 39-43 | `accept_issue` | `not_emitted` | `closure_contract_missing` | `残す価値がある項目だけ写す / 解決時は追記する` |

## Triage Buckets

### Promote To Detector Work

- `capability_scope_overclaim`
- `abstract_output_surface_missing`
- `abstract_material_contract_missing`
- `evaluation_axis_missing`
- `repair_routing_contract_missing`
- `routing_threshold_contract_missing`
- `mapping_contract_missing`
- `acceptance_contract_missing`
- `closure_contract_missing`
- `priority_decision_contract_missing`
- `handoff_enrichment_contract_missing`

### Add Suppression Fixtures

- Convention README examples should not emit source-prose expression findings.
- A document-title referent plus immediate boundary bullets can satisfy
  demonstrative reference for `これは...` in a README introduction.

### Rewrite-Only Candidates

Some candidates are worth making clearer in the source document but should not
automatically become global detector rules until more corpus examples exist:

- `interoperate without guessing`.
- `base contract wins only where a repository profile is absent or silent`.
- `fresh-eyes査読を補助材料として挟むかの確認`.
- `ハーネス工学とオーケストレーションに近い`.
- `未決定は悪ではない。隠れた未決定が悪い。`.

## Human Review Points

- Decide whether `all/every` wording should be globally warned when it appears
  in LLM capability claims.
- Decide whether metaphorical continuity wording such as `濃度` should be
  rewritten in README prose or only constrained by nearby schema references.
- Decide whether broad control-plane claims such as `資源全体を見渡す` should be
  globally warned unless they name scope, source, priority rule, and owner.
- Decide whether `写像する` / `補う` / `閉じる` should become a general contract
  family for control-plane and audit-handoff documents.
- Decide whether example-context suppression should be broad for all
  convention documentation or limited to explicitly marked examples.
