# Dogfood: README Expansion

Date: 2026-06-01 JST

## Purpose

Use `semantic-guard` on a small real task: expanding this project's README so a new reader can understand the purpose, usage, status, output contract, and limits.

## Reproduction Commands

Representative commands used during these dogfood passes:

```sh
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.md
uv run --python 3.13 --project . semantic-guard evaluate-fixtures --include-passed
uv run --python 3.13 --project . python -m unittest discover -s tests -v
```

## Input Requirement

`semantic-guard` should help guide a README update without turning the task into fake ceremony. The README should explain:

- what `semantic-guard` is
- when to use it
- how to run the CLI
- how to configure the MCP server
- what JSON shape it returns
- what its current limitations are

## Pre-Implementation Audit Observations

- `understand-target` passed once stakeholders, constraints, assumptions, unknowns, and validation route were stated explicitly.
- `audit-request` warned that the request bundled several requirements into one and fixed the solution as README work.
- The bundled-requirement warning was useful; the README update was split into sections.
- The solution-bias warning was acceptable because README expansion was the explicit dogfood task.
- `audit-plan` passed after objective, non-goals, deliverables, work breakdown, risks, verification, validation, rollback, and evidence were included.

## Implementation Notes

Changed only documentation:

- `README.md`
- this dogfood note

No audit logic was changed.

## Post-Implementation Audit Observations

- `python -m unittest discover -s tests -v` passed: 4 tests OK.
- `audit-diff` passed for the documentation-only change and identified two changed files.
- Running `audit-request` directly on `README.md` produced warnings, but this was partly a misuse: README prose is not a requirement statement.
- The warnings still exposed a real weakness: the current lexical matcher can over-warn on words such as `enough` and security-related adjectives, including when those words appear in explanatory prose rather than requirement language.
- This suggests a later improvement: add an input-kind or audit-mode distinction, for example `requirement`, `plan`, `document`, and `diff-summary`.

## Early Finding

The tool is useful for forcing tacit context into text. It is also blunt: it relies heavily on lexical cues, so good prompts need to state context explicitly or the tool reports missing fields that a human reader may infer.

## Follow-Up: Input Kind

The first dogfood pass showed that `README.md` was being treated like a requirement statement when passed to `audit-request`. This produced noisy warnings for explanatory words such as `enough` and security-related adjectives.

Follow-up implementation:

- Added `--kind requirement|plan|document|diff-summary` to the CLI.
- Added `kind` to the MCP tools where input shape matters.
- Added a document audit path that checks purpose, audience/use, status/scope, usage, output contract, and limitations without applying requirement-only atomicity or ambiguous-requirement wording checks.

## Follow-Up: Document Validity

The next pass tightened `kind=document` beyond section coverage:

- warns when usage is described without a runnable command or code block
- warns when output/schema/contract is mentioned without naming core return fields
- warns when a document makes strong completion, safety, security, correctness, or authority claims without scoping or evidence
- keeps scoped statements such as `prototype`, `not a release gate`, and `does not replace review` from being treated as overclaims

This still does not grade prose style. It only catches a few document-level validity failures that matter for a public-facing prototype README.

## Follow-Up: Claim, Evidence, Limitation

The latest pass added a light claim trace for `kind=document`:

- extracts candidate claims by section
- attaches nearby evidence snippets such as code blocks, commands, examples, verification notes, and results
- attaches nearby limitation snippets such as prototype, heuristic, not-a-release-gate, and does-not-replace-review statements
- warns when a strong claim appears without nearby evidence or limitation

This is deliberately heuristic. It is meant to expose unsupported claims, not to prove that prose is true.

## Follow-Up Request: Real-Use Audit Quality

Later dogfooding on the `releasable-strand` visualizer requirements showed a useful boundary for the current system.

Observed value:

- It is practical as a checklist-like audit surface for requirements and design work.
- It reliably pushes hidden context into text: unknowns, non-goals, output contracts, verification evidence, acceptance criteria, and residual risk.
- In the visualizer work, warnings about weak `unknowns`, `audience_or_use`, `output_or_contract`, and validation evidence led to better requirements documents.
- It is especially useful before implementation, where the main risk is meaning drift rather than syntax or test failure.

Observed limits:

- It should be treated as a coarse sieve, not an oracle or final judge.
- Japanese and free-form prose can still trigger false missing-field warnings, such as plan sections being present but not recognized as `work_breakdown` or `verification_plan`.
- Some `audit_diff` findings are too generic, for example identity/storage warnings without enough concrete affected text.
- The system sometimes reports evidence weakness correctly, but does not clearly distinguish "cannot be proven because no implementation exists yet" from "the document overclaims."
- It can be vocabulary-driven: if the wording matches the expected surface form, it may score well even when a domain expert still needs to judge meaning.

Requested improvements:

- Add stronger Japanese synonym and heading recognition for fields such as objective, deliverables, work breakdown, risks, verification, validation, rollback, evidence, non-goals, and unknowns.
- When a required field is reported missing, include the nearest rejected candidate text so the user can tell whether this is a real gap or parser weakness.
- Split findings into `actionable`, `generic caution`, and `possible false positive` so Codex can decide how much to trust each warning.
- Make `audit_diff` findings more specific by naming the likely affected semantic boundary, such as identity, display identifier, persistence, membership, source of truth, permission, or evidence.
- Add an explicit "no implementation evidence available" condition for document-only phases, so the tool warns without implying the document could have proved runtime correctness.
- Keep the final acceptance decision outside the tool. The desired role is "annoying but useful reviewer," not release gate or judge.

Acceptance direction:

- A future version should preserve the current strength: forcing hidden assumptions and validation routes into the artifact.
- It should reduce noisy warnings on well-structured Japanese documents.
- It should make every warning either directly actionable or clearly marked as a broad caution.

## Follow-Up Implementation: Real-Use Audit Quality

Implemented changes:

- Expanded Japanese synonym and heading recognition for plan fields, including objective, non-goals, deliverables, work breakdown, risks, verification, validation, rollback, evidence, and unknowns or decision points.
- Added `warning_class` to findings with `actionable`, `generic caution`, and `possible false positive`.
- Added `nearest_candidates` for missing-field findings so rejected nearby lines are visible.
- Added document-only `no_implementation_evidence_available` reporting, so unsupported runtime claims are scoped as document evidence gaps rather than impossible evidence demands.
- Replaced the generic `audit_diff` meaning warning with named semantic boundaries: identity, display identifier, persistence, membership, source of truth, permission, and evidence.
- Kept final acceptance outside the tool; this change only improves diagnostic output.

Regression coverage:

- Japanese synonym headings can pass a structured plan.
- Missing verification can expose a nearby rejected `点検方針` candidate and mark the warning as a possible false positive.
- Document overclaims without runtime evidence are marked as document-only evidence cautions.
- `audit_diff` names likely semantic boundaries while preserving the existing false-positive guards for command words, audit paths, and reviewer-role prose.

## Follow-Up Request: Escalate Undecidable Cases

New design direction:

- The deterministic audit should detect when it cannot tell whether a warning is a real gap or parser weakness.
- Those undecidable cases should be routed to the isolated `codex exec` reviewer.
- The exec reviewer must remain a supplement generator, not a judge.
- Default behavior must stay dry-run so ordinary audits do not unexpectedly start a model process.

Implemented changes:

- Added an escalation decision layer that detects possible false positives, high-severity missing fields with nearby candidates, high-impact generic cautions, document-only runtime evidence gaps, high-impact semantic boundaries, and low-confidence warn results.
- Added `review-if-needed` CLI and `review_if_needed_tool` MCP entrypoints.
- Kept existing `audit_*` calls light; escalation is an explicit follow-up path.
- Kept `--execute` / `execute=true` as the only path that starts `codex exec`.

Regression coverage:

- Passed audit results do not trigger review.
- Possible false positive findings produce an escalation payload.
- Dry-run escalation builds the isolated reviewer command and prompt without executing.
- Execute mode can run through a supplied runner and validate schema-shaped reviewer output.

## Follow-Up Request: Implementation-Engineering Signals

New design direction:

- There is not a single authoritative field named "implementation engineering" in the same way as requirements engineering or project management.
- The closest usable bodies of knowledge are software construction, software life-cycle processes, software product quality, software operations, and security-focused software development guidance.
- These should not be imported as compliance claims.
- They should be compressed into small failure modes that `semantic-guard` can actually detect.

Reference areas used:

- SWEBOK software construction, testing, operations, and security.
- ISO/IEC/IEEE 12207 software life-cycle processes.
- ISO/IEC 25010 product quality characteristics.
- NIST SSDF security-development practices.

Implemented changes:

- Added `audit_diff` implementation signals for public CLI/API/MCP/output-contract changes.
- Added failure-prone operation detection for subprocess, shell, file I/O, JSON parsing, network-like calls, migrations, and environment access when failure handling is not visible.
- Added operational-observability detection for background execution, schedulers, notifications, monitoring, retry, and external execution when status/log/reporting evidence is not visible.
- Added dependency/runtime detection for manifest, lockfile, Docker, workflow, and runtime configuration changes.
- Added `finish_check` behavior evidence detection so public CLI/API/MCP/schema work needs a representative execution, smoke test, output-contract check, or explicit non-run reason.

Regression coverage:

- Public contract changes are marked as compatibility cautions.
- Failure-prone operations without timeout or exception handling are marked as reliability cautions.
- Timeout and exception handling suppress the failure-handling warning.
- Operational changes without log/status/report evidence are marked as operations cautions.
- Dependency/runtime changes are marked as dependency cautions.
- Finish checks for public behavior warn when only unit-test evidence is present and pass the behavior check when representative execution is recorded.

## Follow-Up Request: Requirements and Planning Engineering Signals

New design direction:

- Requirements engineering and planning guidance should be used as source material, not as a compliance costume.
- The useful additions are small recurring failure modes that make Codex work drift: unnamed stakeholders, unmeasured quality claims, bundled requirements, ownerless validation, and uncontrolled scope changes.
- These checks should stay weaker than human acceptance. They are prompts to inspect, not final judgments.

Reference areas used:

- ISO/IEC/IEEE 29148 requirements engineering.
- BABOK requirements analysis, validation, prioritization, and lifecycle management.
- PMBOK value, stakeholder, scope, quality, monitoring, and change-control guidance.
- ISO 21502 project-management planning and control guidance.
- NASA SEH stakeholder expectations, validation, technical assessment, and technical baseline/change control.

Implemented changes:

- Added `audit_request` requirement signals for missing stakeholder/source.
- Added quality-request detection when performance, safety, reliability, maintainability, usability, or similar claims lack a measurement condition or acceptance basis.
- Added priority detection when multiple requirements appear bundled without priority or ordering.
- Added uncertainty classification detection when "maybe/probably/たぶん" style wording is not separated as unknown, hypothesis, pending decision, or related status.
- Added `audit_plan` planning signals for validation owner, progress control, and change control.
- Added rule-catalog entries for each new requirements/planning concern.

Regression coverage:

- Requirements without stakeholder/source are flagged.
- Quality claims without measurement are flagged; threshold-backed quality claims are not.
- Bundled requirements without priority are flagged.
- Unclassified uncertainty is flagged.
- Plans with validation but no acceptance owner are flagged.
- Multi-step plans without progress checkpoints are flagged.
- Migration/configuration-sensitive plans without change control are flagged.

## Follow-Up Request: Detailed Requirement Achievement Profile

New design direction:

- The previous requirement signals were too coarse.
- A requirement should expose what counts as achieved, how that will be checked, what evidence remains, and what result causes rejection or rework.
- User-facing requirements also need a small scenario: who acts, under what condition, with what input, and what output or state is expected.

Implemented changes:

- Added `details.requirement_profile` with visible acceptance criteria, verification method, evidence artifact, acceptance owner, rejection condition, and scenario context.
- Added `achievement_criteria` warning when verification language exists but no success, acceptance, done, or pass condition is visible.
- Added `verification_method_detail` warning when confirmation is generic and not tied to test, inspection, analysis, demonstration, measurement, review, or representative execution.
- Added `evidence_artifact` warning when verification exists but no command result, test result, log, screenshot, JSON output, report, or record is named.
- Added `rejection_condition` warning for sensitive requirements such as safety, permission, deletion, migration, release, operation, persistence, and payment.
- Added `scenario_context` warning for user-facing or input/output requirements without usage scene, input condition, operation context, or expected output.

Regression coverage:

- Weak "動作確認する" requirements now expose missing achievement criteria, verification method detail, and evidence artifact.
- Detailed requirements with scenario, acceptance criterion, benchmark method, evidence artifact, and rejection condition pass those detailed checks.
- Sensitive requirements without rejection conditions are flagged.
- User-facing screen/search requirements without scenario context are flagged.

## Follow-Up Request: Requirement Statement Structure Profile

New design direction:

- A requirement can have acceptance criteria and still be structurally weak.
- "Improve X" is not enough unless it names an observable behavior or state change.
- User-facing and interface requirements need the condition under which they fire, the expected result, and the contract surface.

Implemented changes:

- Added `details.requirement_structure` with observable behavior, precondition or trigger, expected result, and interface contract.
- Added `observable_behavior` warning for vague improvement/support/optimization language without a concrete behavior.
- Added `precondition_or_trigger` warning for UI, input, search, notification, API, CLI, or JSON requirements without a firing condition.
- Added `expected_result` warning for operation/input/interface requirements without output, state change, error, rejection, notification, or persistence result.
- Added `interface_contract` warning for API, CLI, MCP, JSON, YAML, CSV, webhook, config, env, and file-format requirements without input/output fields, format, status code, error, default, example, or schema terms.

Regression coverage:

- Vague behavior such as "report feature improvement" is flagged.
- User-facing search requirements without trigger or expected result are flagged.
- API/JSON requirements without a contract are flagged.
- API/JSON requirements with request field, response fields, status, and rejection condition pass the new interface checks.

## Follow-Up Request: Detailed Planning Engineering Profile

New design direction:

- A plan can name objective, deliverables, validation, and rollback while still being weak as a plan.
- Planning needs not only "what to do", but also how the work is decomposed, sequenced, resourced, controlled, and gated.
- The implementation should stay scoped to `audit-plan`; requirement and diff audits should not silently absorb planning concerns.

Research basis:

- NASA technical planning and SEMP guidance emphasize technical organization, process application, risk integration, assessment, corrective action, and living plan updates.
- ISO 21502 frames project management guidance across delivery approaches, while ISO 21511 covers work breakdown structures.
- PMI WBS guidance treats deliverable-oriented decomposition as a basis for scope, schedule, cost, resource, and risk management.
- PMI risk guidance emphasizes risk event, probability, impact, response planning, contingency, and continuous review.

Implemented changes:

- Added `details.planning_structure` with work-package decomposition, dependency sequence, estimate/resource basis, risk response, control baseline, and decision gate.
- Added `work_package_decomposition` warning for broad deliverables or multi-artifact plans without WBS/work-package style decomposition.
- Added `dependency_sequence` warning for multi-step implementation plans without predecessor/successor, order, dependency, parallelism, or blocker information.
- Added `estimation_or_resource_basis` warning for implementation/migration/release/configuration plans without effort, time, owner, capacity, resource, or explicit "no extra dependency" basis.
- Added `risk_response` warning when risks are named but no mitigation, detection, fallback, contingency, hold, retry, or owner is visible.
- Added `control_baseline` warning when progress or completion is discussed without a baseline, milestone condition, metric, threshold, or judgment criterion.
- Added `decision_gate` warning for release, migration, operation, configuration, permission, safety, deletion, or production work without go/no-go, approval, stop condition, or human gate.

Regression coverage:

- Structured plans now pass only when they include decomposition, sequence, resource basis, risk response, control baseline, and relevant decision gates.
- Broad multi-artifact plans without work-package decomposition are flagged.
- Multi-step plans without dependency sequence and resource basis are flagged.
- Plans that list risks without response and progress without a baseline are flagged.
- Release/configuration plans without a decision gate are flagged.

## Follow-Up Request: Fixture Evaluation Harness

New design direction:

- The audit engine should not only accumulate rules; it needs a way to measure whether rule changes preserve expected behavior.
- Existing fixture expectations were useful inside unittest, but not available as a first-class CLI output for calibration or regression review.
- This does not claim statistical precision/recall yet. It is a local calibration harness that makes fixture pass/fail visible as JSON.

Implemented changes:

- Added `semantic_guard.evaluation` for loading `*.expected.json` fixtures, running the matching audit phase, and comparing status, score, categories, missing fields, and selected details.
- Added `semantic-guard evaluate-fixtures` with `--path` and `--include-passed`.
- Added `evaluate_fixtures_tool` to the MCP server.
- The command returns total, passed, failed, pass rate, phase counts, expected/actual status counts, and per-fixture issues.
- Added tests proving the current fixture tree passes and an intentionally wrong fixture reports a status issue.

Regression coverage:

- Current fixture tree evaluates to pass.
- A synthetic mismatched expectation evaluates to fail with a structured issue.

## Follow-Up Request: Fixture Labels And Metrics

New design direction:

- The fixture harness should distinguish "the fixture passed" from "the rule found the specific thing this fixture was meant to exercise".
- Phase 1/2 of the maturity plan needs a small fixture expectation schema for expected and forbidden findings, then metrics over that schema.
- The result should be explicit that these are fixture-label calibration metrics, not broad statistical precision/recall.

Implemented changes:

- Added optional fixture `labels.expected_findings` and `labels.forbidden_findings`.
- Finding label specs can match severity, category, warning class, finding/evidence/suggested-fix substrings, basis substring, semantic boundary, and nearest-candidate substring.
- `evaluate-fixtures` now aggregates fixture-label true positives, false negatives, true negatives, false positives, expected-finding recall, and forbidden-finding clean rate.
- Added category hit counts, missing-field hit counts, and expected-status to actual-status confusion counts.
- Added representative labels to existing ambiguous request, overclaim document, and command-defaults diff fixtures.

Regression coverage:

- Existing fixtures still pass with labels.
- A synthetic label fixture records true positive and true negative metrics.
- A synthetic bad label fixture records false positive and false negative metrics and fails evaluation.

## Follow-Up Request: Logical Audit Slice

New design direction:

- The audit system should move closer to logically inspectable derivations without pretending to prove natural language truth.
- The first implementation slice should stay narrow and cover only `req.verifiability.acceptance_missing`.
- The old behavior must not degrade: existing `status`, `score`, fixture expectations, CLI, MCP, and human final decision boundaries should survive.
- Derivation output should explain accepted facts, checked counterconditions, missing obligations, and derivation steps.

Implemented changes:

- Added first-class fact extraction for `input.kind.requirement`, verification language, acceptance criteria, verification method, evidence artifact, and external acceptance route context.
- Added an executable predicate for `req.verifiability.acceptance_missing`.
- Added scoped `finding.derivation` and `details.logical_trace` output for the target rule.
- Kept candidate, rejected, unknown, and conflict facts from satisfying obligations.
- Added fixture expectation keys for derivation and logical-trace invariants.
- Kept LLM reviewer output as candidate supplement material only, not accepted facts or final decisions.

Regression coverage:

- The target derivation derives only when the existing target rule finding is emitted.
- Detailed requirements keep `status=pass` and `score=1.0` while receiving a satisfied logical trace.
- Secondary obligations can be visible in the trace without creating new legacy findings.
- Fixture evaluation can assert derivation status, derivation rule id, missing obligation, countercondition, fact, and logical trace rule.

## Follow-Up Request: Phases 3-6 Completion

New design direction:

- The harness should move from "rules exist" to "rules are observable, measurable, and repairable".
- Phase 3 should expand the corpus with both good and bad examples across requirement, plan, diff, and finish checks.
- Phase 4 should report rule-level hit data, not only finding categories.
- Phase 5 should make warnings easier to act on by attaching structured repair hints.
- Phase 6 should expose traceability and context-specific severity profiles without turning the tool into a final judge.

Implemented changes:

- Added additional fixtures for detailed search requirements, missing interface contracts, weak and good release/configuration plans, subprocess security diffs, and public-behavior finish evidence.
- Added `rule_id` to findings when a finding maps to the rule catalog.
- Added `repair` payloads with repair kind, target field, minimal example, human-decision flag, source, rule id, and remediation text.
- Extended fixture labels with `expected_rules` and `forbidden_rules`.
- Added aggregate `rule_hits`, expected-rule recall, and forbidden-rule clean rate to `evaluate-fixtures`.
- Added severity profiles: `default`, `dogfood`, `exploratory`, `release`, and `safety`.
- Added `--profile` to text audit commands and `profile` to MCP text audit tools.
- Added `trace-report` CLI and `trace_report_tool` MCP entrypoint for request-plan-diff-finish trace reports.
- Updated README to document rule ids, repair hints, severity profiles, trace reports, and rule-level fixture metrics.

Regression coverage:

- Focused regression suite passed: 61 tests OK across core, evaluation, fixtures, severity profiles, traceability, and MCP tools.
- `evaluate-fixtures --include-passed` passed 12/12 fixtures with pass rate 1.0.
- Rule-level fixture metrics reported 10 expected rules matched, 0 missed, 9 forbidden rules clean, and 0 forbidden matched.
- `audit-request` on a vague request now emits rule ids and structured repair hints for mapped findings.
- `audit-plan --profile release` upgrades release/control/governance findings while recording `details.severity_profile.adjustments`.
- `trace-report` links request, plan, diff, and finish segments and reports segment gaps separately from blocked underlying audits.

Remaining caution:

- `rule_id` mapping is still heuristic. Exact catalog matches are stable; substring fallback can miss wording changes.
- `repair` is intentionally a hint, not an automatic edit.
- `trace-report` currently uses vocabulary overlap, so it catches weak trace but does not prove semantic satisfaction.
- Severity profiles change priority and status pressure; they do not replace human release, safety, or acceptance decisions.

## Follow-Up Request: Ambiguity Tolerance Layer

New design direction:

- The deterministic audit should not jump straight from "exactly recognized" to "missing".
- Near misses should say whether they are matched, partial, rejected, missing, not applicable, or unknown.
- Exec review should receive only structured uncertainty, not every parser discomfort.

Implemented changes:

- Added optional finding fields: `match_status`, `confidence`, `ambiguity_reasons`, and `candidate_matches`.
- Added deterministic candidate extraction in `semantic_guard.matching`.
- Kept `nearest_candidates` as a compatibility projection from structured candidates.
- Added `details.match_status_counts`, `details.confidence_counts`, and `details.ambiguity_reason_counts`.
- Added fixture label matching for match status, confidence, ambiguity reason, candidate status, candidate `matched_by`, and candidate `rejected_by`.
- Added aggregate `match_status_hits`, `confidence_hits`, and `ambiguity_reason_hits` to `evaluate-fixtures`.
- Extended `review-if-needed` to escalate explicit unknown matches, high-severity partial matches, high-impact low-confidence findings, and selected structured ambiguity reasons.
- Updated the ambiguity design document and README.

Regression coverage:

- English `Work Package Decomposition` headings now satisfy `work_breakdown`.
- Weak synonym candidates such as `点検方針` remain warnings, but now carry `match_status=partial`, `confidence=medium`, `ambiguity_reasons=["weak_synonym"]`, and a structured candidate.
- Structured ambiguity labels are accepted by fixture evaluation.
- Escalation can now use structured match diagnostics, not only `warning_class`.

Remaining caution:

- Profile-specific escalation pressure is still not implemented.
- Candidate scoring remains deterministic and lexical; it is not a semantic proof.

## Follow-Up Implementation: Trace Vocabulary Normalization

Design direction:

- `trace-report` should not depend only on raw shared words.
- Event-like tags are useful, but they should remain trace diagnostics rather than becoming a persistent event store or a Releasable Strand object model.
- Tags should bridge vocabulary gaps such as `受入条件` versus `Definition of Done`, not prove that the artifact is semantically complete.

Implemented changes:

- Added `trace_tags` extraction for request, plan, diff, finish, and evidence segments.
- Added alias-based canonical tags for acceptance, evidence, verification, validation, output contract, risk, rollback, work breakdown, traceability, vocabulary, and related engineering concerns.
- Added optional payload-provided per-segment `tags` for cases where the caller already knows the intended trace tag.
- Extended trace links with `raw_strength`, `tag_strength`, `shared_tags`, `match_status`, `confidence`, and `ambiguity_reasons`.
- When raw vocabulary is weak but normalized tags bridge the link, the link records `trace_vocabulary_gap` and is capped at medium strength.

Regression coverage:

- Japanese request text using `受入条件`, `検証方法`, and `出力項目` now links to English finish text using `Done when`, `Verification`, and `Output fields` through shared normalized tags.
- Payload tags can connect segments through an event-like trace tag without adding a persistent event identity.

Remaining caution:

- Trace tags are a diagnostic index, not proof of semantic satisfaction.
- The canonical tag vocabulary is deliberately small and should grow only through observed dogfood cases.
- Profile-specific escalation pressure is still not implemented.

## Follow-Up Implementation: Not Applicable Suppression Traces

Intent:

- Make absent warnings more explainable when a rule is intentionally scoped out.
- Keep suppression evidence separate from findings so it cannot masquerade as acceptance.
- Preserve the responsibility boundary: deterministic audit explains, but a human still decides whether the scoped-out reason is acceptable.

Implemented changes:

- Added `details.suppressed_rules` for explicit suppression traces.
- Added `details.suppressed_rule_counts` aggregated by rule id.
- `audit-request` now records `req.scope.non_goals_missing` as `match_status: "not_applicable"` when a scope boundary such as `対象外` is present.
- `audit-plan` now records `plan.control.change_control_missing` as `match_status: "not_applicable"` when a migration/release/configuration-heavy plan includes explicit change control.

Boundary:

- Suppression traces are not findings.
- They do not change `status`, `score`, `missing`, severity profile behavior, or final human decision.
- They only explain why a warning did not appear.

## Follow-Up Implementation: Dependency Runtime Token Boundary

Observed issue:

- `audit-diff` treated `decision` as a dependency/runtime signal because the old matcher searched for `ci` by raw substring.

Implemented changes:

- Added word-boundary matching for English dependency/runtime terms.
- Kept Japanese terms such as `依存` and `実行環境` on the existing substring path.
- Added regression coverage so `decision` does not trigger `dependency_runtime`, while `CI/CD runtime` still does.

Boundary:

- This does not change the dependency-runtime rule, severity, score, or final human decision boundary.
- It only narrows one lexical false positive.

## Follow-Up Implementation: Vocabulary Negotiation Surface

Design direction:

- Generic engineering terms can be normalized automatically.
- Domain-specific terms should not be accepted automatically, because a wrong mapping can damage the target domain's meaning.
- The useful behavior is to expose terms that need agreement, not to pretend the tool understands every local vocabulary.

Implemented changes:

- Added `unresolved_terms` to `trace-report` for domain-specific terms that need vocabulary agreement.
- Added `suggested_tags` as candidate mappings only; they are not accepted trace tags.
- Added `vocabulary_decisions` with per-term `status` values such as `needs_decision`, `accepted`, `rejected`, and `deferred`.
- Added optional `vocabulary_profile` input. Only terms marked `accepted` are promoted into `trace_tags`.
- Kept rejected and deferred terms visible without using them as trace evidence.

Regression coverage:

- Releasable Strand terms such as `ビード` and `ストランド` appear as unresolved terms and suggested tags, but are not automatically added to `trace_tags`.
- An accepted `vocabulary_profile` entry can promote `ビード` to `rs.bead`.
- Rejected or deferred terms remain outside `trace_tags`.

Remaining caution:

- The candidate dictionary is deliberately small and local to observed dogfood cases.
- `vocabulary_profile` is not persisted by `semantic-guard`; the caller or project documents remain the source of agreement.

## Follow-Up Implementation: Conflict Fix Plan Stage 1-7

Source:

- `docs/conflict-audit-2026-06-02.md`
- `docs/conflict-fix-plan-2026-06-02.md`

Design direction:

- Start with fixture and rule-catalog visibility before changing semantic output.
- Treat an explicit scope boundary or change-control boundary as a satisfied non-emitted rule, not as `not_applicable`.
- Keep compatibility fields, but make the less ambiguous field the preferred reading path.
- Separate embedded audit warnings from trace-link quality.
- Keep profile pressure and final human decision boundaries out of this pass.

Implemented changes:

- Added `rule_catalog_coverage` to `evaluate-fixtures`, including local `unhit_rule_ids`.
- Added conflict fixtures for bounded whole-plan wording, bounded work-package requests, and docs-only evidence-boundary diffs.
- Added `details.non_emitted_rules` with `emission_status`; `details.suppressed_rules` remains as a compatibility projection.
- Added `details.diagnostics` as a normalized summary for emitted findings, non-emitted rules, and field-match diagnostics.
- Changed explicit `対象外` and `変更統制` traces from `match_status: not_applicable` to `emission_status: satisfied`, `match_status: matched`.
- Added `summary.audit_status`, `summary.trace_status`, `summary.vocabulary_status`, and `summary.aggregate_status_reason` to `trace-report`.
- Added `details.severity_profile.profiled_score` while keeping top-level `score` as the base deterministic score.
- Added `details.document_claim_summary` so weak unsupported document claims can remain visible even when the document audit passes.
- Narrowed broad-scope and docs-only evidence false positives for the observed conflict cases.

Boundary:

- This pass does not implement C10 profile-specific escalation pressure.
- This pass does not change `final_human_decision`; human acceptance remains outside deterministic audit output.
- `rule_catalog_coverage` is local fixture calibration, not statistical coverage.

Verification:

- `python -m unittest discover -s tests` passed 110 tests.
- `semantic-guard evaluate-fixtures` passed 15/15 fixtures with pass rate 1.0.
- Representative `audit-request` output now shows `details.non_emitted_rules` with `emission_status: satisfied` for explicit `対象外`.
- Representative `audit-plan --profile release` output now shows both `base_score` and `profiled_score`.

## Follow-Up Request: Comparative Advantage And Adoption

Source:

- `docs/comparative-advantage-and-adoption-2026-06-03.ja.md`

Observed value:

- The current system has a defensible niche as a phase-spanning semantic audit layer for agent work.
- Its strongest property is not scanner power, workflow execution, or platform governance, but externalizing request, plan, diff, finish, trace, evidence, and human review points as inspectable audit data.
- The human final decision boundary remains a meaningful advantage over designs that imply automatic acceptance.

Observed limits:

- It should not claim parity with Semgrep or Snyk for security scanning.
- It should not claim parity with Planu for readiness scoring, acceptance-criteria quality, coverage gap, or adversarial challenge.
- It should not claim parity with Spec Kit for resumable workflow execution and human gates.
- It should not claim parity with Harness MCP for operation audit logs, risk policy, and elicitation.

Requested improvements:

- Add an external evidence contract as a sidecar artifact, not as an automatic `finish-check` or `trace-report` integration.
- Add acceptance-criteria quality and gap reports inspired by Planu, without importing a full spec platform or changing `audit-request` / `audit-plan` output schemas.
- Add gate suggestion reports that surface human decision points without deciding accept/reject inside the tool.
- Add a failure-isolated operation audit log for `semantic-guard` CLI/MCP executions, while keeping it out of audit scoring.
- Add scanner evidence readers for Semgrep and Snyk JSON output, while keeping `semantic-guard` out of the scanner-engine role and out of automatic scan gating.
- Add an adversarial scenario report for mutable operations, migrations, search/list/export, critical operations, out-of-scope conflicts, and prior-decision conflicts.

Boundary:

- Do not vendor-lock the system to one scanner.
- Do not turn the system into a release gate.
- Do not turn the system into a workflow shell executor before trust, dry-run, allowlist, and audit-log foundations exist.
- Do not fold these companion reports into existing audit phase functions until a separate human decision changes this boundary.
