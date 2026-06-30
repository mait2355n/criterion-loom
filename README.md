# Criterion Loom

Criterion Loom is a meaning-first audit CLI, MCP server, and companion Codex
skill for Codex work.

It turns ambiguity and missing information in requests, plans, change
explanations, and completion claims into JSON audit results. The public project
name is Criterion Loom; the package, CLI, and MCP server name is
`semantic-guard`.

It does not approve AI output as correct. Its audit output is meant to feed an
agentic revision loop: Codex or another AI agent can use findings to revise
request framing, plans, change explanations, and completion claims before
presenting them again. The same output also gives humans material for final
`accept`, `request_revision`, or `defer` decisions.

## At A Glance

| Need | Start Here |
| --- | --- |
| Try the CLI | `uv run --python 3.13 --project . semantic-guard --help` |
| Understand the public model | `docs/naming.md` |
| Use the Codex companion skill | `skills/semantic-implementation/` |
| Read Japanese guidance | `README.ja.md` and `docs/ja/` |
| Check repository readiness | `docs/release/public-repository-readiness.md` |
| Report sensitive issues | `SECURITY.md` |

It externalizes checks that otherwise stay implicit in an agent's reasoning:

- `explore-request`: target users, material ambiguities, and questions to ask before a spec exists
- `audit-request`: purpose, scope, non-goals, verification conditions, and uncertainty
- `audit-plan`: work breakdown, order, risk, verification, rollback, and completion evidence
- `audit-diff`: meaning, public contracts, failure handling, tests, documentation, and minimality
- `finish-check`: execution evidence, residual risk, and human confirmation points
- `audit-decision-state`: undecided, unknown, hypothetical, inferred, value-judgment, and evidence-gap statements
- JSON output, JSON Schema, fixtures, unit tests, and `doctor` checks for local verification
- a companion Codex skill that routes Codex work through the same audit-and-revision flow

## Quick Start

Run from a checkout root:

```sh
uv run --python 3.13 --project . semantic-guard explore-request --text "Build a split-bill app"
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.md
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
uv run --python 3.13 --project . semantic-guard doctor
```

The commands return JSON. A `pass` means the current deterministic checks did
not stop the input; it is not a human acceptance decision.

## Public Naming

Criterion Loom has four public-facing parts:

| Public Name | Role | Technical Surface |
| --- | --- | --- |
| **Loom Guide** | Codex skill that routes work through the audit flow | `skills/semantic-implementation/` |
| **Need Thread** | requirements audit for need, scope, stakeholder, verification, quality, priority, and uncertainty | `audit-request` |
| **Plan Warp** | planning audit for work breakdown, sequence, validation, risk, progress, rollback, minimality, and evidence | `audit-plan` |
| **Change Weft** | implementation audit for diff meaning, public contracts, failure handling, minimality, tests, and completion evidence | `audit-diff` and `finish-check` |

The implementation still exposes additional support commands such as `explore-request`, `llm-explore-request`, `understand-target`, `audit-decision-state`, `trace-report`, `audit-conventions`, `conventions-catalog`, `doctor`, `audit-result-schema`, `request-exploration-review-schema`, `rule-detector-map`, LLM reviewer helpers, and acceptance-review bundle tools. They support the four-part public shape, but they are not separate public pillars.

## Status

This is a research prototype, not a finished requirements engineering product.

The current implementation uses vocabulary rules and lightweight structural
checks. It does not fully understand natural language, and fixture evaluation is
local regression coverage rather than a precision or recall measurement for
general documents. It is useful for dogfooding Codex workflows and making missing
assumptions visible, but it should not be treated as an authoritative
requirements, safety, or release gate.

Human final decision is still required. The tool can drive agent-side revision
and prepare audit output, reviewer supplements, and acceptance-review bundles,
but `final_human_decision.status` stays `pending` until a person chooses
`accept`, `request_revision`, or `defer`.

For the naming map, see `docs/naming.md` or the Japanese version at `docs/ja/naming.md`.

For public positioning against MCP servers, security scanners, and agent skills, see `docs/public-comparison-2026-06-02.md` or the Japanese version at `docs/public-comparison-2026-06-02.ja.md`.

For Japanese usage notes and demonstration commands, see `README.ja.md` and `docs/ja/`.

For repository contribution, security-reporting, change-log, and publication hygiene, see `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`, and `docs/release/github-publication-checklist.md`.

## When To Use

Use Criterion Loom when a task can be harmed by misunderstanding meaning, intent, scope, or verification:

- non-trivial implementation plans
- agentic work loops where Codex should revise its own plan, diff explanation, or finish claim after explicit audit feedback
- feature or requirements clarification
- documentation that explains a system's purpose or limits
- refactors, migrations, and behavior changes
- creative canon or knowledge-base organization where uncertainty must be preserved
- completion checks that need evidence and residual-risk notes

Do not use it for obvious typo fixes, one-line shell commands, or purely mechanical edits where the overhead would be fake rigor.

## Install

Clone the repository and run commands from the checkout root:

```sh
git clone https://github.com/mait2355n/criterion-loom.git criterion-loom
cd criterion-loom
uv run --python 3.13 --project . semantic-guard --help
```

`pyproject.toml` requires Python 3.11 or newer. The examples use Python 3.13 because that is the public snapshot verification interpreter.

When running from another directory, point `uv --project` at the checkout:

```sh
export SG_PROJECT=/absolute/path/to/semantic-guard
uv run --python 3.13 --project "$SG_PROJECT" semantic-guard --help
```

## Audit Phases

`semantic-guard` exposes the commands behind Criterion Loom's public parts.

| Public Part | Command | Question |
| --- | --- | --- |
| support | `explore-request` | Which local preflight gaps are visible before a spec exists? |
| support | `llm-explore-request` | What can an isolated LLM extract, and what material questions remain? |
| support | `understand-target` | Does Codex understand the thing being changed and what must be preserved? |
| support | `audit-decision-state` | Which decisions, unknowns, hypotheses, inferences, value judgments, and evidence gaps must be exposed before management? |
| **Need Thread** | `audit-request` | Is the request clear, necessary, scoped, verifiable, and not prematurely turned into a solution? |
| **Plan Warp** | `audit-plan` | Does the plan cover deliverables, work breakdown, risk, verification, validation, rollback, minimality, and evidence? |
| **Change Weft** | `audit-diff` | What could this change break in meaning, quality, security, tests, docs, operations, or minimality? |
| **Change Weft** | `finish-check` | Is there enough evidence to claim completion, and what risk remains? |

## CLI

Run the CLI with `uv` from the checkout root:

```sh
uv run --python 3.13 --project . semantic-guard explore-request --text "..."
uv run --python 3.13 --project . semantic-guard llm-explore-request --text "..." --execute
uv run --python 3.13 --project . semantic-guard understand-target --text "..."
uv run --python 3.13 --project . semantic-guard audit-decision-state --text "..."
uv run --python 3.13 --project . semantic-guard audit-request --file request.md
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.md
uv run --python 3.13 --project . semantic-guard audit-plan --profile release --file plan.md
git diff | uv run --python 3.13 --project . semantic-guard audit-diff --intent "..."
uv run --python 3.13 --project . semantic-guard finish-check --text "..." --evidence "..."
uv run --python 3.13 --project . semantic-guard audit-conventions --text "MCP tool returns JSON output."
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
uv run --python 3.13 --project . semantic-guard doctor
uv run --python 3.13 --project . semantic-guard audit-result-schema
uv run --python 3.13 --project . semantic-guard request-exploration-review-schema
uv run --python 3.13 --project . semantic-guard rule-detector-map
uv run --python 3.13 --project . semantic-guard conventions-catalog
uv run --python 3.13 --project . semantic-guard trace-report --file trace-input.json
```

Each command reads from standard input when neither `--text` nor `--file` is provided.
For `audit-diff` standard input only, a leading `Intent:` or `Intent：` line is treated like `--intent` when `--intent` is omitted, and that metadata line is removed from the diff body. Explicit `--intent` wins. Hunk lines such as `+Intent:` or `-Intent:` are not metadata.

For `audit-request`, logical trace detail is controlled by `--logical-trace summary|full|none`. The CLI default is `summary`: it keeps `details.logical_trace_summary` and omits the full `details.logical_trace`. Use `--logical-trace full` when detailed fact and predicate records are needed.

Use `--kind` when the input shape matters:

- `requirement`: default for `audit-request`; applies requirement-quality checks
- `plan`: default for `audit-plan`; applies plan-completeness checks
- `document`: treats the input as explanatory prose, avoids requirement-only warnings, and checks document coverage, runnable examples, output-contract terms, unsupported overclaims, and claim/evidence/limitation triples
- `diff-summary`: default for `audit-diff`; treats the input as a change summary or unified diff. `details.changed_files` uses explicit diff headers first, then conservative path-like file names from change-summary lines.

Use `evaluate-fixtures` to run the local calibration fixtures as JSON-producing evaluation data. It reports total, passed, failed, pass rate, phase counts, expected/actual status counts, fixture-label metrics, category hits, missing-field hits, derivation hit counts, logical-trace rule hit counts, rule catalog coverage, status confusion, and failing rows. Use `--include-passed` when you need every fixture row, not just failures.

Use `doctor` to check the local project shape, Python version, schemas, MCP dependency import, optional `codex` binary presence, rule-detector mapping coverage, CI workflow content, and fixture evaluation. It returns JSON with `status`, `checks`, `summary`, and `next_actions`.

Use `audit-result-schema` to print the common JSON Schema for normal audit results. Use `rule-detector-map` to inspect the current mapping from catalog rule ids to detector functions, predicate ids, and source paths.

Use `audit-conventions` to check whether a plan, diff summary, document, or coding note mentions public I/O without the baseline output envelope, versioned field/type shape, error shape, CLI stream roles, durable-record uncertainty markers, repository profile boundary, or representative output-contract verification. The baseline source lives under `docs/conventions/`; use `conventions-catalog` to print the machine-readable catalog.

Use `--profile default|dogfood|exploratory|release|safety` on text audit commands when the same finding should be weighted differently by situation. For example, `release` upgrades release/configuration control and governance findings, while `exploratory` prevents exploration notes from becoming blocker-heavy.

Use `explore-request` as a deterministic preflight for early ideas that are not ready to be audited as requirements. It returns the common audit-result JSON envelope to stdout with `phase`, `status`, `score`, `findings`, `missing`, `next_actions`, and `details`. `details.schema_version` is `request-exploration/v1`; typed detail fields include `audience_hypotheses`, `material_ambiguities`, `questions`, `question_policy`, `spec_outline`, and `non_decisions`. It adds no custom failure shape: CLI usage errors keep the existing argparse message on stderr and exit code 2, while audited-material warnings or blockers remain JSON `status` values on stdout. The command records hypotheses, inferred unknowns, and pending decisions as such; it does not turn them into requirements.

Use `llm-explore-request` when exhaustive pre-spec elicitation is needed. It builds an isolated `codex exec` exploration reviewer prompt from the original text, optional context, and deterministic preflight output, then asks the LLM to extract all visible facts, inferences, hypotheses, unknowns, and pending human decisions before generating every material missing question. Dry-run is the default; use `--execute` to run Codex and validate JSON output against `schemas/request-exploration-review.schema.json`. A valid result uses `schema_version: "request-exploration-review/v1"` and includes `extracted_information`, `audience_hypotheses`, `material_ambiguities`, `questions`, `spec_outline`, `non_decisions`, and `limits`. This is still not approval, implementation planning, or final acceptance.

MCP callers that need progress visibility for LLM exploration can use `llm_explore_request_start_tool` and then poll `llm_exploration_status_tool`. Exploration jobs are process-local and report `state`, `running`, `process_finished`, `exploration_received`, `response_state`, `valid`, `timed_out`, and `errors`.

Use `audit-decision-state` when the important question is not "what is correct?" but "what has or has not been decided?". It exposes pending decisions, unknowns, hypotheses, inferences, one-sided observations, time-dependent claims, value judgments, and evidence gaps. It does not resolve them. `details.schema_version` is `decision-state-audit/v1`, and `details.decision_state_report.management_handoff_items` is shaped for a management or control-plane record with `kind`, `uncertainty_kind`, `decision_state`, `source_excerpt`, `suggested_owner`, `needed_for`, `blocking_status`, `next_action`, and `review_at`. It adds no custom failure path: usage failures keep the existing argparse message on stderr and exit code 2, while audited-material warnings stay in stdout JSON with `status`, `findings`, and `next_actions`. If handoff items are saved as durable records, include ISO 8601 time with timezone, evidence source, fact/inference/hypothesis/unknown/pending-decision separation, and decision owner when known.

When saving audit output or completion notes as durable evidence, include an ISO 8601 timestamp with timezone, the source command or reviewer source, and whether each recorded item is a fact, inference, hypothesis, unknown, or pending decision. Pending decisions should name the decision owner when known.

Use `trace-report` with a JSON object containing any of `request`, `plan`, `diff`, `finish`, `evidence`, `context`, `strict`, `profile`, optional per-segment `tags`, and optional `vocabulary_profile`. It runs the available segment audits, builds vocabulary-overlap links between request, plan, diff, and finish, normalizes lightweight trace tags such as acceptance, evidence, verification, output contract, risk, and rollback, then reports missing segments, blocked segment audits, weak trace links, unresolved domain terms, suggested trace tags, and a trace summary.

Fixture expectation files can optionally include `labels` to turn examples into calibration data:

```json
{
  "labels": {
    "expected_findings": [
      {"category": "verifiability", "finding_contains": "達成確認方法"}
    ],
    "forbidden_findings": [
      {"category": "security"}
    ],
    "expected_rules": [
      "req.verifiability.acceptance_missing"
    ],
    "forbidden_rules": [
      "diff.security.sensitive_surface_change"
    ]
  }
}
```

`expected_findings` count matched findings as fixture-level true positives and missed findings as false negatives. `forbidden_findings` count absent findings as true negatives and matched findings as false positives. `expected_rules` and `forbidden_rules` do the same at rule-id level and feed `metrics.rule_hits`. Fixture expectations may also name `derivation_status`, `derivation_rule_id`, `derivation_missing_obligation`, `derivation_countercondition`, `derivation_fact`, `logical_trace_rule`, and `logical_trace_summary_rule` for the narrow logical-audit slice. These derivation metrics are hit counts over fixture rows, not statistical precision/recall. `rule_catalog_coverage.unhit_rule_ids` lists catalog rule ids that are not yet covered by fixture rule labels. These are calibration labels over the local fixture set, not statistical precision/recall for arbitrary documents.

## MCP Server

Start the MCP server over stdio:

```sh
uv run --python 3.13 --project . semantic-guard-mcp
```

Example Codex configuration:

```toml
[mcp_servers.semantic_guard]
command = "uv"
args = [
  "run", "--python", "3.13",
  "--project", "/absolute/path/to/semantic-guard",
  "semantic-guard-mcp"
]
required = false
startup_timeout_sec = 20
tool_timeout_sec = 60
```

The MCP server exposes:

- `explore_request_tool`
- `llm_explore_request_tool`
- `llm_explore_request_start_tool`
- `llm_exploration_status_tool`
- `understand_target_tool`
- `audit_request_tool` with `kind`
- `audit_decision_state_tool` with `kind`
- `audit_plan_tool` with `kind`
- `audit_diff_tool` with `kind`
- `finish_check_tool`
- `audit_conventions_tool`
- `conventions_catalog_tool`
- `evaluate_fixtures_tool`
- `trace_report_tool`
- `llm_review_command_tool`
- `llm_review_run_tool`
- `review_if_needed_tool`
- `audit_result_schema_tool`
- `request_exploration_review_schema_tool`
- `rule_detector_map_tool`
- `doctor_tool`
- `acceptance_bundle_template_tool`
- `validate_acceptance_bundle_tool`

The text audit tools also accept `profile` with the same severity profile names as the CLI.

## Loom Guide Skill Integration

The companion Codex skill is publicly called **Loom Guide** and lives at `skills/semantic-implementation/SKILL.md`.

Use it when Codex needs to route non-trivial work through meaning, requirement,
plan, diff, finish, optional LLM reviewer, and final human-review checks. The
skill prefers the `semantic-guard` MCP server when available and falls back to
the local CLI from a checkout root.

Install or update the local Codex skill from the repository root:

```sh
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
mkdir -p "$CODEX_HOME/skills"
rsync -a --delete \
  skills/semantic-implementation/ \
  "$CODEX_HOME/skills/semantic-implementation/"
```

The wheel also bundles this skill under `skills/semantic-implementation/` so
package archives carry the same companion instructions. Installing the wheel
does not automatically install or enable the Codex skill.

If you only have an installed wheel, run this with the Python environment where
`semantic_guard` is installed:

```sh
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
SKILL_SRC="$(
  python - <<'PY'
from pathlib import Path
import semantic_guard

print(Path(semantic_guard.__file__).resolve().parents[1] / "skills" / "semantic-implementation")
PY
)"
test -d "$SKILL_SRC"
mkdir -p "$CODEX_HOME/skills"
rsync -a --delete "$SKILL_SRC/" "$CODEX_HOME/skills/semantic-implementation/"
```

After either sync path, Codex can load the skill from
`$CODEX_HOME/skills/semantic-implementation`.

Start a new Codex session after syncing if an older copy of the skill may
already have been loaded.

Verify the local audit tool and MCP registration separately:

```sh
uv run --python 3.13 --project . semantic-guard audit-request \
  --kind document --file skills/semantic-implementation/SKILL.md
codex mcp list --json
```

The `codex mcp list --json` output should include an enabled
`semantic_guard` server when MCP routing is configured. If it is absent, the
skill can still use the CLI fallback from a checkout root.

See `skills/semantic-implementation/README.md` for the skill install, sync, and
verification contract.

## Output Shape

All phases return the same JSON shape:

```json
{
  "phase": "audit_plan",
  "status": "pass",
  "score": 1.0,
  "findings": [],
  "missing": [],
  "next_actions": [],
  "details": {}
}
```

`status` is one of:

- `pass`: no blocking or meaningful warning was emitted by the current checks
- `warn`: the task can continue, but missing context or risk should be considered
- `block`: a critical field is absent for strict-mode work

Findings include severity, category, basis, evidence, suggested fix, and whether a human decision is needed.
Each finding also carries `warning_class`:

- `actionable`: the warning points to a concrete missing field or check.
- `generic caution`: the warning is a broad review prompt, not a release decision.
- `possible false positive`: nearby rejected text exists, so the parser may have missed a valid human-readable field.

When a required field is missing, a finding may include `nearest_candidates` with nearby rejected lines. These candidates are not accepted evidence; they help decide whether the warning is a real gap or a parser weakness.

When a finding matches the rule catalog, it includes `rule_id` and a structured `repair` payload. The repair names the repair kind, target field, minimal example, whether human judgment is needed, source, rule id, and remediation text. This is an edit hint, not an automatic patch.

The common audit-result JSON Schema lives at `schemas/audit-result.schema.json` and can be printed with:

```sh
uv run --python 3.13 --project . semantic-guard audit-result-schema
```

For the current logical-audit slices, `audit-request` may attach `finding.derivation` to `req.verifiability.acceptance_missing`, `req.achievement.criteria_missing`, `req.verification.method_detail_missing`, `req.evidence.artifact_missing`, `req.acceptance.rejection_condition_missing`, `req.context.scenario_missing`, and `req.structure.observable_behavior_missing`. The derivation record includes `schema_version`, `derivation_scope`, `rule_id`, categorical `status`, accepted facts used, checked counterconditions, missing obligations, derivation steps, and unresolved unknowns. This is a rule-and-fact derivation only. It does not prove natural-language truth, semantic satisfaction, release readiness, or final acceptance.

Missing-field and near-miss findings may also include deterministic tolerance diagnostics:

- `match_status`: `matched`, `partial`, `rejected`, `missing`, `not_applicable`, or `unknown`
- `confidence`: `high`, `medium`, or `low`
- `ambiguity_reasons`: stable reason strings such as `weak_synonym`, `heading_only`, or `negated_context`
- `candidate_matches`: short candidate excerpts with `score`, `status`, `confidence`, `matched_by`, `rejected_by`, and `ambiguity_reasons`

These fields explain why text was accepted, partially accepted, rejected, or sent toward review. They do not change the meaning of `status` or `score`.

When a rule is not emitted, `details.non_emitted_rules` records why. Each entry can include `rule_id`, `emission_status`, `match_status`, `reason`, `source`, `confidence`, and nearby `evidence`. Use `emission_status: "satisfied"` when the input supplies the required boundary, such as `対象外` or `変更統制`; reserve `match_status: "not_applicable"` for a real counter-condition. `details.suppressed_rules` remains as a compatibility projection of the same entries. These traces are not findings and do not change `status`, `score`, or human acceptance.

`details.diagnostics` normalizes the major diagnostic channels: emitted findings, non-emitted rules, and field-match diagnostics. It is a summary for routing and review, not a separate acceptance decision.

Severity profiles add `details.severity_profile` and may adjust finding severities before status is recalculated. This keeps the base rule stable while letting dogfood, exploratory, release, or safety contexts weight the same rule differently. The top-level `score` remains the base deterministic score; `details.severity_profile.profiled_score` shows the score after profile severity adjustments.

For `audit-diff`, meaning warnings may include `semantic_boundaries` such as `identity`, `display_identifier`, `persistence`, `membership`, `source_of_truth`, `permission`, and `evidence`.
`audit-diff` also reports `details.implementation_signals` when a change appears to touch implementation-engineering concerns such as public CLI/API/MCP contracts, failure-prone I/O or subprocess paths, operational observability, or dependency/runtime configuration. Evidence excerpts are compact nearby snippets; they are meant for orientation, not complete proof text.
`audit-diff` may also report `details.complexity_growth` and a `diff.implementation.complexity_growth` finding when added control flow, classes, async, or exception paths look like complexity growth that needs a reason.

For `audit-request`, `details.requirement_signals` reports likely requirements-engineering gaps such as missing stakeholder/source, weak achievement criteria, underspecified verification method, missing evidence artifact, quality claims without measurement, missing rejection conditions, missing scenario context, multi-requirement inputs without priority, and unclassified uncertainty.
`details.requirement_profile` extracts the visible achievement profile: acceptance criteria, verification method, evidence artifact, acceptance owner, rejection condition, and scenario context.
`details.requirement_structure` extracts the visible statement structure: observable behavior, precondition or trigger, expected result, and interface contract.
`details.logical_trace_summary` is the compact first-read view for logical audit. It lists each evaluated rule with `rule_id`, categorical `status`, emitted `finding_ids`, and small counts for obligations, counterconditions, unknowns, conflicts, and derivation steps. It intentionally omits fact excerpts and evidence spans. CLI and MCP `audit-request` calls return this summary by default.
`details.logical_trace` records the full extracted facts and executable predicate results for the current request logical-audit rules. Candidate, rejected, unknown, and conflict facts are not treated as accepted facts. `details.diagnostics.logical_trace` summarizes routing counts for the same trace; none of these fields change `status`, `score`, or human acceptance.

For `audit-plan`, `details.planning_signals` reports likely planning gaps such as missing validation owner, missing work-package decomposition, missing dependency sequence, missing estimate/resource basis, missing risk response, missing progress control, missing control baseline, missing change control, missing minimality justification for new dependencies or abstractions, and missing decision gates for migration, release, operation, or configuration-heavy plans.
`details.planning_structure` extracts the visible planning structure: work-package decomposition, dependency sequence, estimate or resource basis, risk response, control baseline, and decision gate.

For `--kind document`, `details.claim_triples` lists candidate claims with nearby evidence and limitation snippets. Long snippets are shortened at line, sentence, or code-block boundaries where possible. `details.document_claim_summary` counts supported, limited, unsupported, and strong unsupported claims. This is a heuristic trace, not a proof system.
Document checks also report whether implementation evidence is absent. That condition scopes the warning: a document-only audit can flag unsupported runtime claims, but it does not pretend the document could prove runtime correctness.

`trace-report` has a trace-specific shape rather than the phase shape. It returns `phase`, `status`, `profile`, per-segment `audits`, `links`, `gaps`, `trace_tags`, `unresolved_terms`, `suggested_tags`, `vocabulary_decisions`, and `summary`. Links keep raw vocabulary overlap, and also include normalized `shared_tags`, `tag_strength`, `match_status`, `confidence`, and `ambiguity_reasons` when tag normalization bridges a wording gap. Domain-specific terms are only suggested by default; `vocabulary_profile` must mark a term as `accepted` before it becomes a trace tag. `summary.audit_status`, `summary.trace_status`, and `summary.vocabulary_status` separate embedded audit warnings from trace-link gaps and vocabulary negotiation. A blocked segment audit blocks the trace report; missing segments and weak links warn.

## Rule Catalog

`semantic-guard` also includes a small rule catalog in `src/semantic_guard/rules.py`.

The catalog records audit rules as engineering-shaped objects with `discipline`, `engineering_basis`, `applies_when`, `does_not_apply_when`, `evidence_required`, `severity_policy`, `finding`, and `remediation`. This keeps rules grounded in requirements engineering, planning, software engineering, secure-development guidance, and semantic preservation instead of letting them become unstructured history notes.

See `docs/rule-model.md` for the model and current coverage.

For the current catalog-to-detector trace, run:

```sh
uv run --python 3.13 --project . semantic-guard rule-detector-map
```

This is a maintenance map. It shows which code path currently backs each catalog rule; it does not prove that the detector has understood arbitrary prose correctly.

## LLM Reviewer

`semantic-guard` includes an experimental `candidate_gap_reviewer` support layer for an isolated LLM reviewer.

This layer can generate a reviewer prompt, expose an output schema, validate the returned JSON shape, and optionally call an isolated `codex exec` reviewer through a dry-run-first adapter. The reviewer is limited to missing-aspect detection, questionable assumptions, phase-specific engineering guidance, rule item reviews, possible `does_not_apply_when` matches, supplement proposals, and human decision points. It must not approve, reject, or decide final acceptance.

Generate a prompt from a JSON review bundle:

```sh
uv run --python 3.13 --project . semantic-guard llm-review-prompt --file review-input.json > review-prompt.md
```

Print the output schema:

```sh
uv run --python 3.13 --project . semantic-guard llm-review-schema > candidate-gap-review.schema.json
```

Validate an LLM review result:

```sh
uv run --python 3.13 --project . semantic-guard validate-llm-review --file review-output.json
```

Build the isolated `codex exec` command without running it:

```sh
uv run --python 3.13 --project . semantic-guard llm-review-command --file review-input.json
```

Run the adapter in dry-run or execute mode:

```sh
uv run --python 3.13 --project . semantic-guard llm-review-run --file review-input.json --dry-run
uv run --python 3.13 --project . semantic-guard llm-review-run --file review-input.json --execute
```

`--execute` starts `codex exec` with an ephemeral read-only sandbox, ignored user config, ignored rules, schema-constrained output, and a timeout. Execution failures are returned separately from valid reviewer JSON.

MCP callers that need progress visibility can use the pollable job tools instead of blocking on the synchronous runner:

- `llm_review_start_tool`: starts an isolated reviewer and returns a `job_id`.
- `review_if_needed_start_tool`: runs the escalation check first, then starts a reviewer job only when review is needed.
- `llm_review_status_tool`: returns `state` as `running`, `completed`, `failed`, `timed_out`, or `not_found`.

The job status also separates process completion from valid review receipt: `process_finished` means the background command ended, while `review_received` means the output parsed and passed the reviewer schema. Invalid JSON and schema mismatch are `failed`, not successful reviewer responses.

See `docs/llm-reviewer.md` for the role boundary and `codex exec` experiment shape.
See `docs/ambiguity-confidence-design.md` for the confidence, match-status, ambiguity-reason, and review-routing-pressure layer used by `review-if-needed`.

## Escalation

`review-if-needed` detects deterministic audit uncertainty, impact, and explicit independent-review value, then prepares an isolated `codex exec` reviewer call when review routing pressure is present.

The pressure score is not a correctness probability and is not a claim that the deterministic audit is wrong. It is a routing signal: "is there enough value in a context-isolated second pass to build or run the reviewer?" The returned `escalation.non_decisions` records that the decision does not approve, reject, clear findings, change audit status, or change final human acceptance.

It is meant for cases where `semantic-guard` can see that its own warning may be incomplete or over-broad:

- a finding is marked `possible false positive`
- a major or blocking missing field has `nearest_candidates`
- a finding has `match_status=unknown`
- a high-impact finding has low deterministic `confidence`
- a structured ambiguity reason such as `negated_context`, `quoted_or_historical`, `trace_vocabulary_gap`, or `high_impact_low_specificity` appears
- a generic caution touches evidence, security, meaning, or semantic boundaries
- document-only audit sees strong runtime claims without implementation evidence
- `audit-diff` touches high-impact boundaries such as `identity`, `persistence`, `source_of_truth`, or `permission`
- a warn result has a low score without a deterministic blocker
- the caller provides `review_context.independent_review_requested` or `review_context.fresh_eyes_requested`
- the caller reports context-contamination risk such as `review_context.self_reviewed` or `review_context.same_agent_planned_and_implemented`
- the caller marks a public or wide change surface with `review_context.public_release`, `review_context.external_publication`, or `review_context.changed_files_count`

The default is dry-run. It returns an `escalation` decision and, when needed, the same dry-run reviewer payload as `llm-review-run`:

```sh
uv run --python 3.13 --project . \
  semantic-guard review-if-needed --file escalation-input.json --dry-run
```

The `escalation` object keeps compatibility fields such as `needed`, `mode`, `target`, `reasons`, `rationale`, and `payload`, and also returns:

- `pressure`: score, level, and score semantics.
- `dimensions`: grouped pressure levels such as uncertainty, impact, countercondition plausibility, context contamination risk, and independent review value.
- `signals`: inspectable weighted inputs that produced the pressure.
- `non_decisions`: explicit things this routing decision does not decide.

Use `--execute` only when the extra review value justifies starting an isolated reviewer:

```sh
uv run --python 3.13 --project . \
  semantic-guard review-if-needed --file escalation-input.json --execute
```

The reviewer still cannot approve, reject, or make the final acceptance decision. Its output is supplement material for the parent Codex or a human reviewer.

## Acceptance Review Bundle

`acceptance_review_bundle` is the final human-review package. It gathers the original request, final artifact, deterministic audits, LLM reviewer material, adopted/rejected/deferred supplements, execution evidence, residual risks, and human review points.

It does not let the LLM make the final decision. `final_human_decision.status` stays `pending` until a person chooses `accept`, `request_revision`, or `defer`.

```sh
uv run --python 3.13 --project . semantic-guard acceptance-bundle-schema
uv run --python 3.13 --project . semantic-guard acceptance-bundle-template --file bundle-input.json
uv run --python 3.13 --project . semantic-guard validate-acceptance-bundle --file acceptance-bundle.json
```

See `docs/acceptance-review-bundle.md` for the schema intent and MCP tools.

## Documentation Map

Start with the public-facing documents:

- `README.md`: current status, setup, command examples, output contract, and limits.
- `docs/public-comparison-2026-06-02.md` and `docs/public-comparison-2026-06-02.ja.md`: public positioning and non-claims.
- `docs/llm-reviewer.md`: LLM reviewer role boundary.
- `docs/acceptance-review-bundle.md`: human-final acceptance material.
- `docs/rule-model.md`: rule catalog structure.
- `docs/fixture-record-design.md`: fixture record format and assertion policy.
- `docs/calibration-report-2026-06-05.md`: current fixture calibration snapshot.
- `skills/semantic-implementation/README.md`: companion Codex skill install and sync contract.
- `skills/semantic-implementation/SKILL.md`: companion Codex skill routing.

Dated design notes, dogfood records, conflict audits, and implementation plans under `docs/` are working records. They can explain why a decision exists, but the README and the public-facing documents above are the safer starting points for publication.

## Development

Run tests:

```sh
uv run --python 3.13 --project . python -m compileall src/semantic_guard tests
uv run --python 3.13 --project . python -m unittest discover -s tests -v
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
uv run --python 3.13 --project . semantic-guard doctor
```

A GitHub Actions CI template is available at `docs/release/ci-workflow-template.yml`.
Restore it as `.github/workflows/ci.yml` when the publishing credential has GitHub
`workflow` scope. It runs compile, unit tests, fixture evaluation, and `doctor`
on Python 3.11 and 3.13.

Fixture regression records live under `tests/fixtures`.

Each fixture pairs an input artifact with a `*.expected.json` file that states the phase, input kind, rationale, and partial expectations for the result. The runner checks stable invariants such as status, finding categories, missing fields, and selected `details` values instead of requiring whole-output equality.

See `docs/fixture-record-design.md` for the record format and assertion policy.

Run a quick MCP smoke test with a Python client:

```sh
uv run --python 3.13 --project . python - <<'PY'
import asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

async def main():
    params = StdioServerParameters(
        command="uv",
        args=["run", "--python", "3.13", "--project", ".", "semantic-guard-mcp"],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print([tool.name for tool in tools.tools])

asyncio.run(main())
PY
```

## License

MIT. See `LICENSE`.

## Limitations

- The current checks are heuristic and vocabulary-driven.
- Japanese heading and synonym recognition is broader than the first prototype, but still lexical.
- The score is a rough signal, not a formal quality measure.
- It can over-warn when context is obvious to a person but not stated in text.
- It can under-warn when the text sounds complete but the real project context contradicts it.
- `nearest_candidates` are diagnostic hints, not accepted requirements.
- `requirement_signals` and `planning_signals` are heuristic cues, not standards-conformance results.
- `finding.derivation` and logical trace fields are scoped derivations over extracted facts and executable predicates. They do not prove the original prose true, complete, safe, semantically satisfied, or accepted.
- `rule_id` and detector mapping are maintenance traces over the local catalog. They do not prove that arbitrary prose was semantically understood, and unmatched findings can still be real.
- Structured `repair` hints are intentionally minimal; they should be reviewed before being applied to a requirement, plan, or document.
- Severity profiles change prioritization, not truth. They do not prove that a release, safety, or exploratory decision is acceptable.
- `trace-report` currently uses lightweight vocabulary overlap plus trace-tag normalization. It can show weak traceability, likely vocabulary gaps, and domain-specific terms that need agreement, but it cannot prove semantic satisfaction.
- `suggested_tags` are not accepted tags. Only explicit `tags` or `vocabulary_profile` entries with `accepted` status are treated as trace tags.
- `semantic_boundaries` name likely affected meaning boundaries; they do not prove actual semantic breakage.
- Implementation signals name likely affected engineering concerns; they do not prove a defect.
- Document audit checks coverage and obvious claim/evidence/limitation problems; it does not judge prose quality deeply.
- It does not replace human judgment, domain review, security review, or acceptance testing.

## Design Notes

The audit model is influenced by requirements engineering, project planning, software life-cycle processes, software construction, product quality models, value engineering, lean engineering, code review practice, software operations, and secure development guidance. The tool does not implement those standards wholesale. It compresses a few useful checks into a local Codex-facing guard surface.

The implementation-engineering checks are deliberately narrow. There is no separate authoritative discipline named "implementation engineering" here; the current rules draw from SWEBOK software construction and operations, ISO/IEC/IEEE 12207 life-cycle processes, ISO/IEC 25010 quality characteristics, and NIST SSDF secure-development guidance.

The requirements and planning checks are also deliberately narrow. They draw from ISO/IEC/IEEE 29148, BABOK, PMBOK, ISO 21502, NASA SEH, value engineering, and lean engineering, but only to catch small recurring failures: unclear achievement criteria, vague verification, missing evidence artifacts, vague behavior, missing preconditions or triggers, missing expected results, thin interface contracts, unnamed stakeholders, unmeasured quality claims, missing rejection conditions, missing scenario context, bundled requirements without priority, unclassified uncertainty, ownerless validation, missing progress checkpoints, missing change-control handling, and added dependencies or abstractions without a minimality basis.
