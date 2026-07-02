# Loom Guide Skill

This directory contains **Loom Guide**, the companion Codex skill for Criterion Loom.

The technical skill directory remains `semantic-implementation`, and the deterministic audit package remains `semantic-guard`.

## Purpose

The skill routes non-trivial Codex work through meaning-first audit steps:
deterministic and LLM-backed exploration for open-ended ideas, target
understanding, request audit, plan audit, diff audit, finish evidence, public
I/O convention audit, optional LLM reviewer material, and final human-review
bundles.

It is an orchestration layer. The deterministic audit core stays in
`semantic-guard`; the skill only decides when and how Codex should call the MCP
tools or CLI fallback.

## Audience And Use

Use this directory when installing the companion skill into a Codex environment
or when reviewing how Codex should invoke `semantic-guard`.

The live Codex skill copy normally lives under:

```sh
$CODEX_HOME/skills/semantic-implementation
```

If `CODEX_HOME` is unset, Codex commonly uses:

```sh
$HOME/.codex/skills/semantic-implementation
```

## Install Or Sync

Run this from the repository root:

```sh
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
mkdir -p "$CODEX_HOME/skills"
rsync -a --delete \
  skills/semantic-implementation/ \
  "$CODEX_HOME/skills/semantic-implementation/"
```

The wheel distribution also includes this directory as
`skills/semantic-implementation/` so the package archive carries the companion
skill. Wheel installation does not automatically install or enable the live
Codex skill.

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

Start a new Codex session after syncing if an older copy may already have been
loaded.

## Verify

Verify the skill document with the local CLI:

```sh
uv run --python 3.13 --project . semantic-guard audit-request \
  --kind document --file skills/semantic-implementation/SKILL.md
uv run --python 3.13 --project . semantic-guard doctor
```

Verify that the MCP server is registered when MCP routing is expected:

```sh
codex mcp list --json
```

The output should include an enabled `semantic_guard` server. If not, the skill
still has a CLI fallback when Codex is working from a `semantic-guard` checkout
or when `SG_PROJECT` points at one.

## Runtime Contract

- Prefer `semantic_guard` MCP tools when available.
- Use `uv run --python 3.13 --project . semantic-guard ...` from a checkout
  root when MCP tools are unavailable.
- Use `SG_PROJECT=/absolute/path/to/semantic-guard` and
  `uv run --python 3.13 --project "$SG_PROJECT" semantic-guard ...` when
  running from another working directory.
- Use `doctor` before trusting a fresh checkout or publication snapshot as the
  audit tool source.
- Use `explore-request` or `explore_request_tool` for fast pre-spec preflight.
- Use `llm-explore-request --execute` or `llm_explore_request_tool(execute=true)`
  when the task needs an isolated LLM to classify visible facts, inferences,
  hypotheses, unknowns, and pending decisions from the supplied input, then
  return schema-valid exploration JSON with material questions and explicit
  limits. This is not a completeness guarantee.
- Use `llm_explore_request_start_tool` plus `llm_exploration_status_tool` when
  LLM exploration should expose running/completed/failed/timed-out state instead
  of blocking until the command returns.
- Use `audit-decision-state` or `audit_decision_state_tool` when the task needs
  decided, undecided, inferred, hypothetical, value-judgment, and evidence-gap
  statements separated before a handoff or control-plane record.
- Use `audit-conventions` or `audit_conventions_tool` when public I/O, CLI,
  MCP, API, durable-record, error-shape, output-schema, or repository-wide
  convention behavior is introduced or changed.
- Use `audit-conventions --kind document` for README, release notes, handoffs,
  public positioning, and skill instructions. Inspect `doc.expression.*` and
  `details.expression_precision.referent_resolutions` for document-expression
  diagnostics; do not treat the top-level `status` alone as a rule-specific
  pass/fail result.
- Use `trace-report` or `trace_report_tool` when request, plan, diff, finish
  evidence, or domain vocabulary need one compact traceability view.
- Treat `review-if-needed` pressure as review routing pressure, not correctness
  probability.
- Use `review_context.independent_review_requested` or `fresh_eyes_requested`
  when a context-isolated second pass is valuable even after a deterministic
  pass.
- Use `llm_review_start_tool` or `review_if_needed_start_tool` plus
  `llm_review_status_tool` when a reviewer call should expose
  running/completed/failed/timed-out state instead of blocking until the command
  returns.
- Treat `review_received=true` or `response_state=valid_review` as the signal
  that schema-valid reviewer material exists. `process_finished=true` alone only
  means the background command ended.
- Treat LLM reviewer output as supplement material only.
- Keep `final_human_decision.status` as `pending` until a human chooses
  `accept`, `request_revision`, or `defer`.

The detailed CLI/MCP output contract is not redefined in this README. See
`references/mcp-contract.md` for schema versions, normal stdout JSON envelope,
stderr and exit-code roles for usage errors, durable-evidence uncertainty
markers, and decision-state handoff fields.

## Non-Goals

- This skill is not a release gate.
- It does not certify requirements, safety, correctness, or security.
- It does not make final acceptance decisions.
- It does not treat document-expression findings as style lint or proof of
  natural-language correctness.
- It should not absorb companion evidence-processing tools into the
  deterministic audit core.
