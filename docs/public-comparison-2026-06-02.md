# Public Comparison 2026-06-02

## Purpose

This document positions `semantic-guard` against public MCP servers and agent skills.

It is a comparison and publication-planning artifact. It does not claim that `semantic-guard` is a security scanner, a release gate, a replacement for human acceptance, or a superior general-purpose MCP server.

## Audience And Use

Use this document when preparing public README copy, release notes, repository descriptions, or comparison notes for `semantic-guard`.

The intended readers are maintainers, reviewers, and potential users deciding whether `semantic-guard` is an MCP server, a skill, a scanner, or a separate audit layer.

Example audit command:

```sh
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file docs/public-comparison-2026-06-02.md
```

The expected use is to cite the category comparison first, then cite dogfood evidence only when making practical-value claims.

## Short Positioning

`semantic-guard` is a meaning-first audit layer for agentic work.

It sits before, during, and after tool use:

- before work: target understanding and request audit.
- before edits: plan audit.
- after edits: diff audit.
- before completion claims: finish check.
- across a task bundle: trace report and acceptance-review material.

It is not mainly a context provider or action executor. It is a structured audit surface for meaning, requirements, planning, traceability, completion evidence, and human decision boundaries.

## Does Comparison Need Actual Trajectory?

No, not for category comparison.

A fair public comparison can be made from declared capabilities, output contracts, and official documentation. For example, a filesystem MCP, GitHub MCP, Context7, Snyk MCP, Semgrep MCP, and Skills each publish enough about their intended use to compare their category and boundary.

Actual trajectory is useful for a different claim: whether `semantic-guard` has worked in practice.

Use trajectory only as evidence, not as the comparison basis:

- Use dogfood artifacts, not raw chat history.
- Use command results, fixture counts, and changed files, not private reasoning.
- Keep the evidence scoped: "these cases improved this local tool" rather than "this proves broad correctness."
- Use trajectory as case-study material after the conceptual comparison is already clear.

Recommended public shape:

- Main comparison: static category comparison.
- Evidence appendix: dogfood trajectories summarized as artifacts and command results.
- No raw conversation transcript unless there is a separate reason to publish it.

## Comparison Axes

| Axis | Why It Matters |
| --- | --- |
| Primary object | What the tool actually works on: context, code, security, workflow, requirement, plan, diff, completion. |
| Output contract | Whether the output is prose, tool action, structured JSON, rule ids, or evidence bundles. |
| Verification surface | Whether the project includes tests, fixtures, regression metrics, or only instructions. |
| False-positive handling | Whether the tool can explain non-emitted warnings, not-applicable rules, weak matches, or advisory warnings. |
| Human decision boundary | Whether the tool preserves final acceptance for a human. |
| Integration mode | MCP server, CLI, skill, hosted service, local scanner, or documentation provider. |
| Failure mode | What kind of misuse would make the tool dangerous or misleading. |

## Ecosystem Comparison

| Category | Public Examples | Primary Use | Where It Is Strong | Where `semantic-guard` Differs |
| --- | --- | --- | --- | --- |
| Reference and utility MCP servers | Model Context Protocol reference servers such as Filesystem, Git, Memory, Sequential Thinking, Fetch, GitHub | Connect an assistant to tools, files, memory, repositories, or reasoning aids | Broad tool access; reusable MCP patterns; concrete operations | `semantic-guard` is not primarily an operation surface. It audits work meaning and completion evidence around tool use. |
| Repository platform MCP | GitHub MCP Server | Repository, issue, pull request, Actions, and code-security access through GitHub APIs | Direct platform integration; toolset and permission scoping | It can expose repository facts and actions. It does not by itself check whether a request, plan, diff, and finish claim preserve meaning. |
| Documentation-grounding MCP | Context7 | Bring current, version-specific documentation and examples into coding prompts | Reduces outdated API and hallucinated documentation risk | It improves source freshness. `semantic-guard` checks whether the task is scoped, verifiable, traceable, and honestly completed. |
| Security scanning MCP | Snyk MCP, Semgrep MCP | Code, dependency, container, IaC, SBOM, and static security scanning | Stronger security-specific rules and vulnerability context | `semantic-guard` should not compete as a vulnerability scanner. Its security checks are coarse audit prompts inside a broader requirements/planning/completion audit. |
| Agent skills | Claude Skills and similar SKILL.md workflow packages | Package instructions, scripts, references, and workflow expertise for repeated tasks | Portable workflow specialization; progressive disclosure; executable helpers | `semantic-implementation` is skill-like, but `semantic-guard` adds CLI/MCP execution, JSON output, rule ids, fixtures, trace reports, and finish checks. |
| Thinking aids | Sequential Thinking MCP and related tools | Structure or externalize reasoning steps | Useful for complex deliberation and revision of thought | Reasoning structure is not the same as acceptance criteria, non-goals, diff risk, fixture calibration, or final evidence. |
| MCP security and supply-chain scanners | Snyk MCP scanning material, MCP security scanners, Semgrep-related tooling | Detect unsafe MCP configuration, vulnerable code, or tool poisoning risk | Better at agentic security posture and supply-chain risk | `semantic-guard` can mention security as one audit category, but its real value is meaning drift, scope drift, and completion-evidence drift. |

## Positioning Against Skills

Skills are close in spirit because they define repeatable workflows.

A public skill usually answers:

- when the assistant should use this workflow.
- what procedure it should follow.
- which scripts, references, or assets it may load.

`semantic-guard` answers a different extra question:

- can the workflow be externally audited as data?

The important difference is executable audit evidence:

| Feature | Ordinary Skill | `semantic-guard` |
| --- | --- | --- |
| Activation instructions | Yes | Via `semantic-implementation` skill |
| Reusable workflow | Yes | Yes |
| CLI commands | Optional | Yes |
| MCP tools | Optional | Yes |
| Structured JSON result | Not inherent | Yes |
| Rule ids and repair hints | Not inherent | Yes |
| Fixture regression | Not inherent | Yes |
| Rule catalog coverage | Not inherent | Yes |
| Completion evidence check | Usually procedural | Executable phase |
| Final human decision boundary | Depends on author | Explicitly preserved |

This makes `semantic-guard` better described as a skill-backed audit engine than as only a skill.

## Positioning Against MCP Servers

Most MCP servers are capability adapters. They let an assistant reach a tool or data source.

`semantic-guard` is closer to a governance adapter:

- It does not make GitHub, files, documentation, or security scanners available.
- It checks whether the agent's use of those things is tied to purpose, scope, verification, evidence, and traceability.

The clean claim is:

> Existing MCP servers extend what the agent can touch. `semantic-guard` audits whether the agent's work remains meaningful, bounded, evidenced, and reviewable.

That claim is strong enough. Do not claim that it replaces security scanners, repository tools, documentation grounding, or human review.

## Differentiators

`semantic-guard` is differentiated by this bundle:

- Five-phase audit path: target, request, plan, diff, finish.
- Input-kind routing, including document-specific audit.
- Requirements-engineering and planning-engineering checks.
- Trace report across request, plan, diff, finish, and evidence.
- Non-emitted rule diagnostics with `emission_status`.
- Diagnostic envelope for findings, non-emitted rules, and field-match evidence.
- Severity profiles with base score and profiled score separated.
- Fixture evaluation with rule catalog coverage.
- LLM reviewer kept as intermediate material only.
- Human final acceptance kept outside deterministic output.

No single public MCP category above appears to be aimed at this same bundle. Individual parts overlap with skills, security scanners, reasoning aids, or documentation MCPs, but the integration point is different.

## Weaknesses And Honest Boundaries

Do not hide these:

- It is still heuristic.
- It is not a formal requirements engine.
- It is not a security scanner.
- Fixture metrics are local calibration, not statistical precision or recall.
- The rule catalog is small.
- Profile-specific escalation pressure remains deferred.
- It can over-warn or under-warn on domain language.
- Human acceptance remains necessary.

These boundaries are not cosmetic. They are part of the product's trust model.

## Publication Recommendation

Publish as:

- `meaning-first audit workbench`
- `agentic workflow audit layer`
- `requirements/planning/completion guard for Codex-style work`
- `skill-backed CLI/MCP audit engine`

Avoid publishing as:

- `AI safety engine`
- `requirements engineering replacement`
- `release gate`
- `security scanner`
- `MCP competitor`
- `autonomous acceptance system`

## Evidence To Publish

Use a compact evidence appendix rather than raw trajectory.

Recommended evidence:

- Current test count and pass result.
- `evaluate-fixtures` result count and pass rate.
- A small example showing `details.non_emitted_rules`.
- A small example showing `rule_catalog_coverage.unhit_rule_ids`.
- A small example showing `trace-report.summary.audit_status` versus `trace_status`.
- A dogfood note link or summary for the README and conflict-fix passes.

Recommended phrasing:

> The comparison is category-based. The dogfood evidence shows that the category is not only theoretical.

## Source Snapshot

Checked on 2026-06-02.

- Model Context Protocol reference servers list Filesystem, Git, Memory, Sequential Thinking, Fetch, GitHub, and related servers: https://github.com/modelcontextprotocol/servers
- GitHub MCP Server documents API-backed repository access, PAT handling, and toolset configuration: https://github.com/github/github-mcp-server
- Context7 states that it brings up-to-date, version-specific documentation and code examples into the assistant prompt: https://context7.com/docs
- Snyk documents a local MCP server through Snyk CLI and profile-based security-scanning tool sets: https://docs.snyk.io/integrations/snyk-studio-agentic-integrations/getting-started-with-snyk-studio
- Semgrep's MCP repository describes security vulnerability scanning and notes that standalone updates moved to the official Semgrep binary: https://github.com/semgrep/mcp
- Claude Skills documentation describes skills as directories with `SKILL.md`, instructions, scripts, and resources loaded for specific tasks: https://claude.com/docs/skills/overview and https://claude.com/docs/skills/how-to
