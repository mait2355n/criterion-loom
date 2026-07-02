# semantic-guard MCP and CLI Contract

The MCP server and CLI share the same audit phases and JSON shape.

## Audience And Use

This contract is for Codex runs that use the `semantic-implementation` skill and for maintainers extending `semantic-guard`.

Use the deterministic audit tools throughout the work. Use deterministic exploration as fast preflight before turning an open-ended idea into a spec, and use LLM exploration when the work needs an isolated reviewer to extract visible facts from the supplied request/context, return schema-valid exploration JSON, and list material questions without claiming completeness. Then use the normal audit phases once requirements or plans exist. Use decision-state audit when the work needs explicit separation of decided, undecided, inferred, hypothetical, value-judgment, and evidence-gap statements. Use LLM reviewer tools as optional intermediate audit support when rule item coverage, missing supplements, counter-conditions, or fresh-eyes review value need a second pass. Use acceptance bundle tools only when preparing a final artifact for human evaluation.
Use `doctor`, `audit-result-schema`, `request-exploration-review-schema`, `rule-detector-map`, `audit-conventions`, `conventions-catalog`, `trace-report`, and `evaluate-fixtures` as support tools for checkout health, output-contract integration, convention checks, traceability, calibration, and catalog maintenance.

## Contract Scope

Repository profile schema_version: `semantic-guard-mcp-cli-contract/v1`.
Repository id: `semantic-guard`.
Public surfaces: CLI commands, MCP tools, JSON audit-result output, JSON helper outputs, schemas, and documented skill routing.
Commands and output shapes are listed below; normal text-audit commands use the shared audit-result envelope with `phase`, `status`, `score`, `findings`, `missing`, `next_actions`, and `details`.
Exception and non-goal boundaries: the contract does not define internal Python APIs, UI behavior, formal requirements proof, release approval, security certification, or final human acceptance.
Representative verification: run `python -m unittest tests.test_cli tests.test_mcp_tools`, a CLI smoke command for the changed surface, `audit-result-schema`, and `doctor` when the public surface changes.
Durable evidence records should include a shallow recovery surface with named `context`, `current_state`, `action` or `next_action`, and `detail_refs` fields, plus ISO 8601 timestamp with timezone, source command or reviewer source, fact versus inference versus hypothesis versus unknown status, pending decision markers, and decision owner when known.

## Phases

- `explore_request`
- `understand_target`
- `audit_request`
- `audit_plan`
- `audit_diff`
- `finish_check`

Support commands such as `audit_decision_state`, `audit_conventions`, `trace_report`, `evaluate_fixtures`, `doctor`, schema commands, and LLM reviewer helpers use the same audit evidence discipline, but they are not separate public pillars.

## Tools

### explore_request

Inputs:

- `text`: open-ended idea, product sketch, feature request, or early artifact proposal.
- `context`: optional known project context.
- `strict`: whether empty or unusable input should block.

Output:

- normal audit-result shape with `phase="explore_request"`.
- CLI output uses the shared JSON envelope on stdout. CLI usage errors keep the existing argparse message on stderr and exit code 2; audited-material warnings or blockers remain JSON `status` values.
- audience or stakeholder hypotheses under `details.audience_hypotheses`.
- material ambiguities under `details.material_ambiguities`.
- necessary questions under `details.questions`.
- a spec outline under `details.spec_outline`.
- non-decisions that state it does not approve the idea, choose the final audience, turn hypotheses into requirements, start implementation, or decide human acceptance.

Use this when the next correct step is elicitation, not implementation. The tool should ask only questions whose answers change scope, data shape, identity, privacy, payment, permissions, external authority, acceptance evidence, or unresolved human decisions.

### llm_explore_request

MCP tool: `llm_explore_request_tool`

CLI:

```sh
semantic-guard llm-explore-request --text "..." --dry-run
semantic-guard llm-explore-request --text "..." --execute
```

Inputs:

- `text`: open-ended idea, product sketch, feature request, or early artifact proposal.
- `context`: optional known project context.
- `execute`: MCP boolean. Defaults to false.
- `--dry-run` or default CLI mode: build prompt and command without launching Codex.
- `--execute`: launch `codex exec` and validate JSON output.
- `model`, `timeout_seconds`, `working_directory`, `include_schema`: optional execution settings.

Output:

- dry-run: command, schema path, prompt, and `execution_status="dry_run"`.
- execute success: `execution_status="valid_exploration"`, `valid=true`, and `exploration` containing `request-exploration-review/v1`.
- execute failure: `execution_status` such as `timeout`, `command_failed`, `invalid_exploration`, or `execution_error`; `valid=false`; errors and process output are preserved.

The exploration result includes `extracted_information`, `audience_hypotheses`, `material_ambiguities`, `questions`, `spec_outline`, `non_decisions`, and `limits`. It is elicitation material only. It does not approve an idea, choose final scope, start implementation, or decide final human acceptance.

### llm_explore_request_start and llm_exploration_status

MCP tools:

- `llm_explore_request_start_tool`
- `llm_exploration_status_tool`

CLI: none. These are MCP-process-local state tools for callers that need progress visibility.

Inputs:

- start: same exploration text, context, model, timeout, working directory, and schema options as `llm_explore_request_tool`, but it always starts a background execution.
- status: `job_id`, plus optional `include_result` and `include_prompt`.

Output:

- start returns `job_id`, `state`, `running`, `done`, command, schema path, and metadata.
- status returns `state` as `queued`, `running`, `completed`, `failed`, `timed_out`, or `not_found`.
- `process_finished` means the background command ended.
- `exploration_received=true` means schema-valid exploration JSON exists.
- `response_state` distinguishes `pending`, `valid_exploration`, `invalid_exploration`, `timed_out`, and `no_valid_exploration`.

The job store is process-local, not durable. Restarting the MCP server loses job state.

### request_exploration_review_schema

MCP tool: `request_exploration_review_schema_tool`

CLI:

```sh
semantic-guard request-exploration-review-schema
```

Output:

- JSON Schema for the LLM exploration reviewer output.
- schema id, required top-level fields, enum values, and nested question/material-ambiguity shapes.

### understand_target

Inputs:

- `text`: user request, project context, or artifact excerpt.
- `context`: optional known context.
- `strict`: whether missing critical fields should block.

Output:

- scores for target understanding fields.
- findings for missing or inferred fields.
- next actions.

### audit_request

Inputs:

- `text`: requirement statement or set.
- `context`: optional target understanding.
- `strict`: whether blockers should stop planning.
- `kind`: input shape. Use `requirement` for requirement statements, `document` for explanatory prose, `plan` for plan text, or `diff-summary` for change summaries.

Output:

- requirement classifications.
- findings for ambiguity, solution bias, unverifiable requirements, conflict, and traceability gaps.
- for `kind=document`, document coverage findings instead of requirement-only wording findings.

### audit_decision_state

MCP tool: `audit_decision_state_tool`

CLI:

```sh
semantic-guard audit-decision-state --text "..."
semantic-guard audit-decision-state --kind document --file handoff.md
```

Inputs:

- `text`: requirement, plan, document, diff summary, handoff, or decision note.
- `context`: optional surrounding context.
- `kind`: input shape. Use `document` for handoffs and explanatory prose.
- `profile`: severity profile.
- `strict`: whether severe decision-state gaps should block.

Output:

- normal audit-result shape with `phase="audit_decision_state"`.
- pending decisions, unknowns, hypotheses, inferences, one-sided observations, time-dependent claims, value judgments, and evidence gaps.
- `details.decision_state_report.management_handoff_items` for possible control-plane or durable-record transfer.

Use this when the important question is "what has or has not been decided?" rather than "is this requirement well written?". It does not resolve uncertainty or decide final acceptance.

### audit_plan

Inputs:

- `plan`: proposed plan.
- `request`: optional original request.
- `context`: optional target understanding.
- `strict`: whether missing objective, non-goals, verification, validation, or rollback should block.
- `kind`: defaults to `plan`.

Output:

- findings for scope, work breakdown, risk, assumptions, verification, validation, and completion evidence.

### audit_diff

Inputs:

- `diff`: unified diff or change summary.
- `intent`: optional request or plan.
- `context`: optional project context.
- `strict`: whether high-impact gaps should block.
- `kind`: defaults to `diff-summary`.

Output:

- findings for traceability, meaning preservation, quality, security, tests, docs, and operational risk.

### finish_check

Inputs:

- `summary`: final change summary.
- `evidence`: commands, test output, file references, screenshots, rendered artifacts, or manual verification notes.
- `context`: optional request or plan.
- `strict`: whether missing acceptance or verification evidence should block.

Output:

- completion status, missing evidence, residual risk, and release blockers.

### audit_result_schema

MCP tool: `audit_result_schema_tool`

CLI:

```sh
semantic-guard audit-result-schema
```

Output:

- common JSON Schema for normal audit results.
- schema id, required top-level fields, status enum, finding fields, and details object policy.

Use this when integrating audit output with external runners, CI, MCP clients, or saved evidence bundles.

### rule_detector_map

MCP tool: `rule_detector_map_tool`

CLI:

```sh
semantic-guard rule-detector-map
```

Output:

- catalog rule count and mapping count.
- one mapping per current rule id with phase, detector id, optional predicate id, source path, and notes.

Use this to inspect whether a catalog rule has an explicit detector trace. This is a maintenance map, not proof that the detector understood arbitrary prose.

### doctor

MCP tool: `doctor_tool`

CLI:

```sh
semantic-guard doctor
semantic-guard doctor --no-fixtures
```

Inputs:

- `project_root`: repository root to inspect.
- `run_fixtures`: whether fixture evaluation should be included.

Output:

- `status`: `pass`, `warn`, or `block`.
- `checks`: per-check status, evidence, and optional details.
- `summary`: pass/warn/block counts.
- `next_actions`: concrete follow-up items when warnings or blockers exist.

Use this before trusting a fresh checkout, publication snapshot, or MCP registration as the audit source.

### audit_conventions

MCP tool: `audit_conventions_tool`

CLI:

```sh
semantic-guard audit-conventions --file plan.md
semantic-guard audit-conventions --text "MCP tool returns JSON output."
```

Inputs:

- `text`: plan, diff summary, coding note, document, or contract excerpt.
- `context`: optional surrounding request or project context.
- `strict`: whether blocker-level convention findings should remain blockers. The initial base contract is draft, so current findings normally warn.
- `kind`: defaults to `document`.
- `profile`: MCP/CLI severity profile.

Output:

- normal audit-result shape with `phase="audit_conventions"`.
- detected public surfaces under `details.surfaces`.
- missing convention rule ids such as `conv.output.envelope`, `conv.error.shape`, `conv.cli.streams`, `conv.record.uncertainty`, `conv.profile.boundary`, and `conv.verification.public_surface`.
- document-expression rule ids such as `doc.expression.target_blurred`, `doc.expression.operation_blurred`, `doc.expression.output_form_missing`, `doc.expression.utility_blurred`, `doc.expression.decision_actor_missing`, `doc.expression.demonstrative_reference_blurred`, `doc.expression.capability_contract_missing`, and `doc.expression.mapping_contract_missing` when `kind=document`.
- `details.expression_precision.referent_resolutions` for demonstrative-reference diagnostics. Status values include `supported`, `ambiguous`, `no_candidate`, and `weak_only`.

Use this when work introduces or changes public I/O, CLI behavior, MCP tools, API responses, durable records, error handling, output schemas, or repository-wide coding conventions.
Also use it for public documentation and skill instructions that make capability, mapping, output-form, utility, or decision-actor claims. These findings are recall-oriented document diagnostics, not style lint or publication approval.

### conventions_catalog

MCP tool: `conventions_catalog_tool`

CLI:

```sh
semantic-guard conventions-catalog
```

Output:

- machine-readable convention catalog loaded from `docs/conventions/base-contract.json`.
- convention status, surfaces, rules, and promotion confirmation points.

Use this when integrating convention checks into tools, skills, or external runners.

### evaluate_fixtures

MCP tool: `evaluate_fixtures_tool`

CLI:

```sh
semantic-guard evaluate-fixtures
semantic-guard evaluate-fixtures --include-passed
```

Inputs:

- `path`: optional fixture root containing `*.expected.json` files.
- `include_passed`: whether passed fixture rows should be included in output.

Output:

- fixture totals, pass/fail status, pass rate, phase counts, expected versus actual status counts, label metrics, category hits, missing-field hits, rule hits, catalog coverage, status confusion, and failing rows.

Use this for local calibration and regression evidence. It is not statistical proof for arbitrary natural-language inputs.

### trace_report

MCP tool: `trace_report_tool`

CLI:

```sh
semantic-guard trace-report --file trace-input.json
```

Inputs:

- JSON object containing any of `request`, `plan`, `diff`, `finish`, `evidence`, `context`, `strict`, `profile`, optional per-segment `tags`, and optional `vocabulary_profile`.

Output:

- segment audit summaries.
- vocabulary-overlap links between request, plan, diff, and finish.
- normalized trace tags such as acceptance, evidence, verification, output contract, risk, and rollback.
- missing segments, blocked segment audits, weak trace links, unresolved domain terms, suggested trace tags, and a trace summary.

Use this when a handoff or final explanation needs a compact traceability view across request, plan, diff, and evidence. It does not replace the underlying audits.

### llm_review_command

MCP tool: `llm_review_command_tool`

CLI:

```sh
semantic-guard llm-review-command --file review-input.json
```

Inputs:

- `payload`: JSON review bundle.
- `model`: optional Codex model. Defaults to the project default.
- `timeout_seconds`: optional timeout used if the command is later executed.
- `working_directory`: optional working root.
- `include_schema`: whether to include the output schema inside the prompt.

Output:

- `executed=false`.
- `execution_status="dry_run"`.
- `command`: list argv for `codex exec`.
- `schema_path`: candidate-gap-review schema path.
- `prompt`: prompt that will be sent to the isolated reviewer.

Use this before executing an LLM reviewer. It is the inspectable route.

### llm_review_run

MCP tool: `llm_review_run_tool`

CLI:

```sh
semantic-guard llm-review-run --file review-input.json --dry-run
semantic-guard llm-review-run --file review-input.json --execute
```

Inputs:

- `payload`: JSON review bundle with at least `candidate`; include `phase` whenever possible.
- `execute`: MCP boolean. Defaults to false.
- `--dry-run` or default CLI mode: build prompt and command without launching Codex.
- `--execute`: launch `codex exec` and validate its JSON output.
- `model`, `timeout_seconds`, `working_directory`, `include_schema`: optional execution settings.

MCP does not expose arbitrary `codex_binary`. This prevents the audit surface from becoming a generic command launcher.

Output:

- dry-run: same as `llm_review_command`.
- execute success: `execution_status="valid_review"`, `valid=true`, and `review` containing `candidate-gap-review/v2`.
- execute failure: `execution_status` such as `timeout`, `command_failed`, `invalid_review`, or `execution_error`; `valid=false`; `errors`, `stdout`, `stderr`, and `failure_kind` are preserved.

The review result is intermediate audit material only. It is not an approval.

### llm_review_start

MCP tool: `llm_review_start_tool`

CLI: none. This is MCP-process-local state and is meant for MCP callers that can poll the same server process.

Inputs:

- `payload`: JSON review bundle with at least `candidate`; include `phase` whenever possible.
- `model`, `timeout_seconds`, `working_directory`, `include_schema`: optional execution settings.

Output:

- `job_id`: identifier for later `llm_review_status_tool` calls.
- `state`: initial job lifecycle state, usually `queued` or `running`.
- `running=true` while the reviewer is still waiting.
- `done=false` until the job reaches a terminal state.
- `response_state="pending"` until the background command has ended.
- `command` and `schema_path` for evidence and debugging.

Use this instead of `llm_review_run_tool(execute=true)` when the caller needs to distinguish "still responding" from failure without blocking the whole call.

### llm_review_status

MCP tool: `llm_review_status_tool`

CLI: none.

Inputs:

- `job_id`: value returned by `llm_review_start_tool` or `review_if_needed_start_tool`.
- `include_result`: include the final reviewer execution result when available. Defaults to true.
- `include_prompt`: include the generated prompt inside the final result. Defaults to false to avoid oversized status payloads.

Output:

- `state`: one of `queued`, `running`, `completed`, `failed`, `timed_out`, or `not_found`.
- `running`: true for `queued` or `running`.
- `done`: true for terminal states.
- `process_finished`: true when the background `codex exec` command has ended.
- `review_received`: true only when stdout parsed as JSON and passed `candidate-gap-review/v2` schema validation.
- `response_state`: `pending`, `valid_review`, `invalid_review`, `timed_out`, `no_valid_review`, or `not_found`.
- `execution_status`, `failure_kind`, `valid`, `timed_out`, and `errors`: execution classification copied from the underlying reviewer result when available.
- `review_result`: final result when `include_result=true` and the job has finished.

Do not treat `process_finished=true` as a valid review. Only `review_received=true` or `response_state="valid_review"` means the isolated reviewer produced schema-valid audit material.

### review_if_needed

MCP tool: `review_if_needed_tool`

CLI:

```sh
semantic-guard review-if-needed --file escalation-input.json --dry-run
semantic-guard review-if-needed --file escalation-input.json --execute
```

Inputs:

- `payload`: JSON escalation bundle with at least `candidate` and `deterministic_audit`.
- `review_context`: optional object for routing value that comes from the work process, such as `independent_review_requested`, `fresh_eyes_requested`, `self_reviewed`, `same_agent_planned_and_implemented`, `long_running_work`, `public_release`, `external_publication`, or `changed_files_count`.
- `execute`: MCP boolean. Defaults to false.
- `model`, `timeout_seconds`, `working_directory`, `include_schema`: optional execution settings.

Output:

- `escalation`: routing decision with `needed`, `reasons`, `pressure`, `dimensions`, `signals`, `non_decisions`, and reviewer `payload`.
- `review_result=null` when `needed=false`.
- dry-run or execution result matching `llm_review_run` when `needed=true`.

`pressure.score` is review routing pressure, not correctness probability. This tool does not approve, reject, clear findings, change audit status, or change final human decision.

### review_if_needed_start

MCP tool: `review_if_needed_start_tool`

CLI: none. Use CLI `review-if-needed --execute` for blocking execution; use this MCP tool for pollable execution.

Inputs:

- `payload`: JSON escalation bundle with at least `candidate` and `deterministic_audit`.
- `review_context`: optional object with the same meaning as `review_if_needed_tool`.
- `model`, `timeout_seconds`, `working_directory`, `include_schema`: optional execution settings.

Output:

- When escalation is not needed: `state="not_needed"`, `job_id=null`, `done=true`, `valid=true`, `review_result=null`, and the `escalation` decision.
- When input is invalid before execution: `state="input_error"`, `job_id=null`, `done=true`, `valid=false`, `errors`, and the `escalation` decision.
- When escalation is needed: same job fields as `llm_review_start_tool`, plus the `escalation` decision. Poll with `llm_review_status_tool`.

The background job store is process-local. Job IDs do not survive MCP server restart and are not a durable queue.

### acceptance_bundle_template

MCP tool: `acceptance_bundle_template_tool`

CLI:

```sh
semantic-guard acceptance-bundle-template --file bundle-input.json
```

Inputs:

- `original_request` or `request`.
- `final_artifact`: object with `kind`, `reference`, and `summary`.
- optional `deterministic_audits`, `llm_reviews`, `adopted_supplements`, `rejected_supplements`, `deferred_supplements`, `execution_evidence`, `residual_risks`, `human_review_points`, `final_human_decision`.

Output:

- `acceptance-review-bundle/v1` JSON scaffold.
- `final_human_decision.status` defaults to `pending`.

Use this when the final artifact is ready for human evaluation. It is not needed for every small edit.

### validate_acceptance_bundle

MCP tool: `validate_acceptance_bundle_tool`

CLI:

```sh
semantic-guard validate-acceptance-bundle --file acceptance-bundle.json
semantic-guard validate-acceptance-bundle --file acceptance-bundle.json --no-strict
```

Inputs:

- `bundle`: acceptance review bundle.
- `strict`: whether to require final-review readiness evidence.

Output:

```json
{
  "valid": true,
  "errors": []
}
```

Strict validation requires at least one deterministic audit, one execution evidence item, and one human review point. Non-strict validation checks only shape and decision boundaries.

## CLI Schemas

```sh
semantic-guard audit-result-schema
semantic-guard request-exploration-review-schema
semantic-guard llm-review-schema
semantic-guard acceptance-bundle-schema
```

Use schema output when integrating with external runners or saving artifacts.

## Finding Shape

```json
{
  "severity": "blocker|major|minor|info",
  "category": "understanding|clarity|scope|traceability|validation|risk|quality|security|meaning|evidence",
  "basis": ["ISO/IEC/IEEE 29148", "BABOK", "PMBOK", "ISO 25010"],
  "evidence": "short excerpt or observation",
  "finding": "what is wrong or missing",
  "suggested_fix": "smallest useful correction",
  "needs_human_decision": false
}
```

## Status Rules

- `block`: at least one blocker finding.
- `warn`: no blocker, at least one major or minor finding.
- `pass`: only info findings or no findings.

Use `block` sparingly but firmly for high-impact work when target purpose, desired state, non-goals, unknowns, validation, verification, or safety evidence is absent.
