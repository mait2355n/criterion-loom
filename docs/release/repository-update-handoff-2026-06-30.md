# Repository Update Handoff

Created: 2026-06-30

## Purpose And Audience

Purpose: transfer the minimum information needed to update repository-facing
material without re-litigating the Criterion Loom positioning.

Audience: the person or Codex session updating the public repository copy,
local working tree, and CORE publication staging for Criterion Loom.

Use: read this file before editing README, companion skill, release, or CORE
staging files. The fuller task plan is
`docs/release/repository-update-plan-2026-06-30.md`.

## Objective

Update repository-facing material so Criterion Loom is presented as:

- a public v0.1 snapshot with the required repository components in place,
- not a finished requirements engineering product or general natural-language understanding system,
- improving audit performance, coverage, and agent-side revision-loop use,
- returning audit findings to Codex or another AI agent for correction before
  final human review.

## Current Decision

Adopt this Japanese short wording:

```text
公開対象の v0.1 snapshot として必要な構成を同梱しています。現在は、監査性能、適用範囲、AIエージェントの修正ループへの接続を継続的に改善しています。
```

Use this longer wording when more context is needed:

```text
Criterion Loom は、Codex 等の AI エージェント作業に対し、依頼、計画、変更説明、完了主張の曖昧さや不足を JSON の監査結果として返す、公開対象の v0.1 snapshot です。

確認対象の構成:
- CLI / MCP server / companion skill
- JSON Schema / fixture / doctor command
- README と docs の公開文書

制限:
- 任意文書を網羅的に処理する要求工学製品ではありません。
- 判定は語彙規則と軽量な構造検査に基づきます。

今後は、監査性能の改善、過警告や見逃しの低減、fixture / corpus の拡充、AI エージェントの修正ループへの戻し方の改善を進めています。
```

## Evidence To Carry Forward

When this handoff was created:

- GitHub `main` resolved to `f3b2d527a844817277ec88ed639a5e1bdfb74ce8`.
- GitHub `main` already had newer `README.md` and `README.ja.md` text for the
  agentic revision-loop position.
- Local `<local-semantic-guard-checkout>` had
  `docs/agent-revision-loop-positioning-2026-06-30.md`, but its top-level
  `README.md` and `README.ja.md` were older than GitHub `main`.
- CORE staging at
  `<CORE-publication-staging-source>`
  was also older than GitHub `main`.
- The package/staging work already includes schemas, fixtures, convention docs,
  and the companion skill bundle in the wheel/sdist build configuration.

Refresh these facts before applying changes if time has passed or the
repository has moved.

## Recommended Source Of Truth

Treat GitHub `main` as the safest current source for public README wording,
because it already contains the agentic revision-loop language described by the
new positioning note.

Then bring local and CORE staging forward, preserving any later local packaging
fixes that are not in GitHub yet, especially:

- `pyproject.toml` force-inclusion of schemas, convention docs, fixtures, and
  `skills/semantic-implementation`.
- installed-wheel skill sync instructions in `README.md`, `README.ja.md`, and
  `skills/semantic-implementation/README.md`.
- `docs/release/repository-update-plan-2026-06-30.md`.
- this handoff file.

## Files To Update Or Check

P0 files:

- `README.md`
- `README.ja.md`
- `docs/acceptance-review-bundle.md`
- `skills/semantic-implementation/README.md`
- `skills/semantic-implementation/SKILL.md`
- `docs/README.md`
- `docs/agent-revision-loop-positioning-2026-06-30.md`

P1 files and directories:

- `docs/ja/public-positioning-note.md`
- `docs/ja/quickstart.md`
- `docs/release/`
- `STAGING-NOTES.md` in CORE staging
- optional public health files if present on GitHub: `CODE_OF_CONDUCT.md`,
  `SUPPORT.md`, `docs/release/publication-format.md`,
  `docs/release/public-repository-readiness.md`

## Required Meaning

Every public-facing update should preserve these statements:

- Criterion Loom produces JSON audit material from requests, plans, change
  explanations, and finish claims.
- The output is useful for an AI agent to revise request framing, plans, change
  explanations, verification, and finish claims.
- The same output can support human `accept`, `request_revision`, or `defer`
  decisions.
- Human final decision is still required.
- Audit performance improvement is ongoing after public v0.1 readiness.

## Do Not Claim

Do not say or imply:

- Criterion Loom automatically approves AI output.
- Criterion Loom replaces human judgment.
- The tool is a finished requirements engineering product.
- Fixture results prove general natural-language understanding accuracy.
- `trace-report` proves causal traceability or durable project management.
- LLM reviewer output can approve, reject, or decide final acceptance.

## CORE Staging Steps

After local repository text is reconciled:

1. Copy the updated public source into
   `<CORE-publication-staging-source>`.
2. Rebuild:

```sh
uv build --out-dir <CORE-publication-staging-dist>
```

3. Update `STAGING-NOTES.md` with the public v0.1 stance, revision-loop
   positioning, audit-performance work, and verification results.
4. Remove generated files from staging source:

```sh
find <CORE-publication-staging-source> -name '__pycache__' -type d -prune -exec rm -rf {} +
find <CORE-publication-staging-source> -name '*.pyc' -type f -delete
find <CORE-publication-staging-source> \( -name '.git' -o -name '.venv' -o -name '.backups' -o -name '__pycache__' -o -name '*.pyc' -o -name '.DS_Store' \) -print
```

The final `find` should print nothing.

## Verification Commands

Run from the repository root:

```sh
uv run --python 3.13 --project . python -m compileall src/semantic_guard tests
uv run --python 3.13 --project . python -m unittest discover -s tests
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
uv run --python 3.13 --project . semantic-guard doctor
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.md
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.ja.md
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file docs/release/repository-update-handoff-2026-06-30.md
```

For the package artifact:

```sh
uv run --python 3.13 --with <CORE-publication-staging-dist>/semantic_guard-0.1.0-py3-none-any.whl --no-project python - <<'PY'
from pathlib import Path
import semantic_guard

skill_dir = Path(semantic_guard.__file__).resolve().parents[1] / "skills" / "semantic-implementation"
assert (skill_dir / "SKILL.md").is_file()
assert (skill_dir / "README.md").is_file()
print(skill_dir)
PY
```

## Done When

The repository update handoff is satisfied when:

- GitHub, local working tree, and CORE staging agree on the public v0.1 stance.
- The public documents use the same revision-loop framing.
- Package archives still include the companion skill bundle and required
  resources.
- Verification commands pass.
- Public wording still keeps the non-approval, human-final-decision, and
  local-fixture limits visible.
