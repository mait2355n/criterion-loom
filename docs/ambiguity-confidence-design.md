# Ambiguity, Confidence, And Review Routing

Criterion Loom uses deterministic audits first. The LLM reviewer is optional intermediate audit material, not a replacement judge.

This document defines the boundary between deterministic findings and `review-if-needed`.

## Audience And Use

This document is for maintainers, MCP integrators, and Codex skill authors who need to decide when deterministic audit output should be enough and when an isolated reviewer should be prepared.

Use it when updating `src/semantic_guard/escalation.py`, wiring `review_if_needed_tool`, explaining LLM reviewer limits, or reviewing whether a new trigger belongs in deterministic findings, review routing, or final human judgment.

## Core Boundary

`review-if-needed` does not estimate whether a candidate is correct.

It estimates review routing pressure: whether an isolated second pass is worth building or running. The returned `pressure.score` has the semantics:

```text
review routing pressure; not correctness probability
```

This pressure never changes `status`, `score`, emitted findings, or `final_human_decision`. It only routes supplemental review material.

## Deterministic Inputs

The deterministic audit remains the first source of truth for emitted findings. `review-if-needed` reads signals such as:

- `warning_class=possible false positive`.
- `match_status=unknown`.
- blocker or major findings with `match_status=partial`.
- high-impact findings with low `confidence`.
- structured `ambiguity_reasons`, especially negated context, quoted or historical context, trace vocabulary gaps, and high-impact low specificity.
- high-severity gaps with `nearest_candidates`.
- generic cautions that touch evidence, security, meaning, or semantic boundaries.
- document-only audits that cannot inspect implementation evidence.
- high-impact semantic boundaries such as identity, persistence, source of truth, and permission.
- low-score warn results without a deterministic blocker.

These signals do not prove the deterministic warning is wrong. They say the warning is hard enough, broad enough, or consequential enough that a context-isolated reviewer may add useful counter-conditions, missing aspects, or human review points.

## Review Context Inputs

The caller may also provide `review_context` when the value of independent review comes from the work process rather than from a deterministic finding.

Supported routing signals include:

- `independent_review_requested` or `fresh_eyes_requested`: explicitly ask for a context-isolated second pass.
- `self_reviewed` or `same_agent_planned_and_implemented`: the same working context may have planned, implemented, and reviewed the work.
- `long_running_work`: a long session increases the chance that local assumptions have hardened.
- `public_release` or `external_publication`: public material benefits from a fresh pass.
- `changed_files_count`: wide change surfaces increase review value.

This preserves the benefit of an uncontaminated reviewer without pretending the system measured "wrongness".

## Usage Example

A deterministic pass can still request an isolated fresh-eyes review when the caller has process-level reasons:

```json
{
  "candidate": "Public documentation was updated and tests were run.",
  "phase": "finish_check",
  "deterministic_audit": {
    "phase": "finish_check",
    "status": "pass",
    "score": 1.0,
    "findings": []
  },
  "review_context": {
    "independent_review_requested": true,
    "self_reviewed": true,
    "public_release": true,
    "changed_files_count": 12
  },
  "non_goals": "The reviewer does not make the acceptance decision."
}
```

Run it in dry-run mode first:

```sh
uv run --python 3.13 --project . \
  semantic-guard review-if-needed --file escalation-input.json --dry-run
```

The result should expose `escalation.pressure`, `escalation.dimensions`, `escalation.signals`, and `escalation.non_decisions`. If `escalation.needed=true`, the dry-run result also shows the reviewer command and prompt without launching `codex exec`.

## Output Shape

`escalation` keeps compatibility keys:

- `needed`
- `mode`
- `target`
- `reasons`
- `rationale`
- `payload`

It also includes:

- `routing_policy`: current routing policy name.
- `pressure`: score, level, and score semantics.
- `dimensions`: grouped pressure levels.
- `signals`: weighted, inspectable inputs.
- `non_decisions`: explicit statements of what the routing decision does not decide.

Pressure levels are descriptive:

- `none`: do not build reviewer material.
- `dry_run_recommended`: build inspectable reviewer material if the caller wants to inspect the prompt.
- `review_recommended`: a second pass likely has value.
- `high_review_pressure`: isolated review is strongly justified, though still not a final decision.

## Non-Decisions

The routing layer explicitly does not:

- score correctness probability.
- accept or reject the candidate.
- clear deterministic findings.
- change audit status or score.
- change final human decision.

The LLM reviewer may return missing aspects, questionable assumptions, possible counter-conditions, supplement proposals, rule item reviews, and human decision points. Those remain candidate material until the parent work or human reviewer adopts, rejects, or defers them.
