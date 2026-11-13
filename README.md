# Criterion Loom

[日本語](README.ja.md) · [Documentation](docs/README.md)

[![CI](https://github.com/mait2355n/criterion-loom/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/mait2355n/criterion-loom/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Make the gap between an engineering claim and its evidence inspectable.

AI-assisted work can leave the difference between fact, hypothesis, missing
evidence, and human acceptance trapped in conversation. Criterion Loom exists
to externalize those distinctions as versioned, inspectable audit artifacts—so
the next correction or decision does not have to trust a fluent summary.

`Criterion Loom` is the public project name. Its current distribution and CLI
are named `semantic-guard` at development version `1.2.0.dev0`; the canonical import package is
`semantic_guard`, and the MCP server entry point is `semantic-guard-mcp`.

## Choose an audit by subject

This development version provides three entry points with separate result
contracts in one installation.

| Subject to audit | CLI | MCP server |
| --- | --- | --- |
| One structured functional requirement, or bounded Japanese direction expressions (canonical v1) | `semantic-guard audit-requirement` / `audit-direction-binding` | `semantic-guard-mcp` |
| Requests, plans, diffs, completion, conventions, and artifact membership (workflow audits) | `semantic-guard workflow COMMAND` | `semantic-guard-workflow-mcp` |
| Requirements with governance material and unresolved obligations (unadopted vNext candidate) | `semantic-guard candidate audit-requirement` | `semantic-guard-vnext-mcp` |

To start a plan or diff audit, use the [integration guide](docs/local-integration.md#入口を選ぶ)
(Japanese). Each entry point retains its own result contract. Combining them
does not constitute a release, candidate-rule adoption, or a deployed-default change.

## Quickstart: one bounded proof

This canonical v1 example checks whether a traversal direction is explicitly
attached to the subject and operation.

Prerequisites: [Python 3.11 or later](https://www.python.org/) and
[`uv`](https://docs.astral.sh/uv/). The current project is run from a source
checkout; no package-index artifact is claimed here. The projection below uses
POSIX shell syntax. Other shells can run the audit command without the pipe and
read the same JSON payload directly.

```sh
git clone https://github.com/mait2355n/criterion-loom.git
cd criterion-loom

uv run --locked --extra nlp-ja semantic-guard audit-direction-binding \
  --text '横一列を左から右へ辿るとき、Aの次の項目はどれですか？' \
  --morphology sudachi \
  | python3 -c 'import json,sys; r=json.load(sys.stdin); print(json.dumps({"state": r["primary_rule_evaluation"]["state"], "direction": r["direction_binding_summary"]["frames"][0]["direction_binding"].get("direction"), "workflow": r["workflow_disposition"]["status"], "human_acceptance": r["acceptance_owner"]["acceptance_status"]}, indent=2))'
```

The selected fields are:

```json
{
  "state": "satisfied",
  "direction": "left_to_right",
  "workflow": "pass",
  "human_acceptance": "pending"
}
```

`satisfied` and `left_to_right` mean that the direction in this input meets the
rule. The `workflow` value `pass` is a disposition under the selected policy;
human acceptance remains `pending`. If a required direction is missing, the
audit does not infer it from convention: it reports a `gap` and sets
`workflow_disposition.status` to `warn`. The projection above displays `null`
when the source result has no `direction` field. The
[direction-binding reference](docs/direction-binding-audit.md) (Japanese) keeps
the paired inputs and exact field states.

## Why this is different

A single score or pass/fail flag would collapse questions that need different
answers. Canonical v1 keeps them apart:

- what the selected rule concludes;
- whether that conclusion is provisional or terminal;
- whether a challenge or conflict remains open;
- how much of the declared subject was actually covered;
- whether the configured workflow should continue, warn, or stop;
- whether a human has accepted anything at all.

The result is decision material, not the decision. Analyzer output cannot grant
itself supporting authority, and `pass` never means correctness, release
approval, security certification, or human acceptance.

## Current public surface

The following four capabilities belong to canonical v1. Workflow audits and
unadopted candidates use the separate entry points listed above.

| Capability | CLI | MCP | Current boundary |
| --- | --- | --- | --- |
| Requirement-relation audit | `audit-requirement` | `audit_requirement_relations_tool` | One seven-field structured functional requirement; morphology is `signal_only`, dependency and caller-supplied LLM analysis are `candidate_only` |
| Direction-binding audit | `audit-direction-binding` | `audit_direction_binding_tool` | Registered scalar and non-scalar Japanese expressions with direct attachment; not unrestricted language understanding |
| Closed schema access | `schema` | `semantic_guard_schema_tool` | 25 known schema names; schema availability does not imply an integrated public workflow |
| Explicit legacy comparison | `shadow-compare` | `shadow_compare_legacy_tool` | Operator-owned external 0.1.0 root; trusted comparison requires baseline digest agreement. The MCP route is disabled by default and requires operator configuration; legacy is not a truth oracle |

The current source also contains candidate lifecycle and assurance contracts.
They are useful design and test material, but they are not silently promoted to
public end-to-end features.

The additional CLI routes `workflow COMMAND` and `candidate COMMAND` select separate
contracts. Their servers are `semantic-guard-workflow-mcp` (27 tools) and
`semantic-guard-vnext-mcp` (three tools); the canonical server retains its four tools.

## Choose an interface

| Surface | Use it when | Start here |
| --- | --- | --- |
| CLI | A person, script, or CI job owns invocation and JSON persistence | `uv run --locked semantic-guard --help` |
| MCP | An agent client needs the tools for its selected audit contract over standard input/output | [Choose a server by audit subject](#choose-an-audit-by-subject) |
| Companion Skill | An agent (Codex or Claude Code) should preserve the audit boundary while planning and implementing work | [`skills/semantic-implementation/`](skills/semantic-implementation/) · [agent setup](docs/local-integration.md#エージェント別の接続) (Japanese) |

The following configuration exposes the four canonical v1 tools to an MCP
client that accepts `command`, `args`, and `cwd`, using a source checkout.
For plan, diff, and other workflow audits, [register the workflow server](docs/local-integration.md#エージェント別の接続)
(Japanese).

```json
{
  "mcpServers": {
    "semantic-guard": {
      "command": "uv",
      "args": ["run", "--locked", "semantic-guard-mcp"],
      "cwd": "/absolute/path/to/criterion-loom"
    }
  }
}
```

Client field names vary; the server contract is standard input/output transport,
not that particular configuration envelope. The companion Skill is repository
material, is not included in the wheel or sdist, and is not installed
automatically.

## Evidence before adjectives

The dated 2026-08-23 1.1.0 evidence records report:

- 608 source tests passing on the recorded Python 3.11 and 3.13 environments;
- 20 packaged-contract checks on one selected local wheel and sdist;
- 24 packaged schemas, four CLI commands, and four MCP tools observed;
- 222 registered direction gap/bound cases replayed on a recorded fresh-wheel
  Sudachi environment;
- the direction-binding slice merged to GitHub main with the defined four CI
  jobs passing.

These observations are bound to the subjects recorded there; they are not an
automatic verification of the current HEAD. They are contract and
registered-case observations, not benchmarks, adoption claims, field accuracy,
unrestricted Japanese coverage, production qualification, or human acceptance.
Read the exact subjects and limits in
[Implementation status](docs/implementation-status.md) (Japanese) and the dated
[direction-binding integration evidence](docs/audits/direction-binding-integration-2026-08-23.md)
(Japanese).

## Documentation

| Goal | Document |
| --- | --- |
| Understand the current package and non-claims | [Current public surface](PUBLIC-SNAPSHOT.md) |
| Run and automate the CLI or MCP server | [Operations guide](docs/operations.md) (Japanese) |
| Compare bound and missing direction-binding results | [Direction-binding audit](docs/direction-binding-audit.md) (Japanese) |
| Inspect implementation and evidence status | [Implementation status](docs/implementation-status.md) (Japanese) |
| Browse current reference, evidence, history, and prototypes | [Documentation map](docs/README.md) |
| Move from the archived 0.1.0 line | [Migration guide](docs/migration-v0.1.0-to-v1.0.0.md) |

Machine schemas and the verification source outrank explanatory prose for field
constraints. Dated reports describe their recorded subject and time; they do
not automatically describe the current tree.

## Version and legacy boundary

The publication-repaired `semantic-guard 0.1.0` predecessor is preserved under
[`legacy/semantic-guard-v0.1.0/`](legacy/semantic-guard-v0.1.0/). Its original
bytes remain anchored by the tag and commit named in the archive manifest. The
old request, plan, diff, finish, convention, reviewer, and acceptance-bundle
commands are not transparent aliases of v1.

Current source identity, field validity, policy adoption, operational default,
and historical preservation are separate states. See the historical
[1.0.0 canonical promotion decision](docs/canonical-promotion-decision.md) and
the [change log](CHANGELOG.md).

Final acceptance, risk acceptance, policy adoption, default cutover, and legacy
retirement remain human decisions.

## Contributing and support

- [Contributing](CONTRIBUTING.md)
- [Support](SUPPORT.md)
- [Security policy](SECURITY.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [MIT License](LICENSE)
