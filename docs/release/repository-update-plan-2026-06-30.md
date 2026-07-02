# Repository Update Plan: Public v0.1 And Audit-Performance Work

Created: 2026-06-30

## Purpose

This file records the repository-side changes needed after adopting the current
positioning:

> Criterion Loom has a publishable first version ready. It is now being
> improved for audit performance, coverage, and agent-side revision-loop use.

This replaces the weaker framing that it is only a rough work-in-progress, but
it must not become an overclaim that Criterion Loom is a finished requirements
engineering product or a general natural-language understanding system.

## Audience And Use

This file is for the repository maintainer and Codex sessions updating the
public repository, CORE publication staging, README copy, companion skill
documentation, and portfolio wording.

Use it before changing public-facing files. It is a task plan and positioning
record, not a release announcement. When it conflicts with live repository
state, refresh the evidence first and update this file or the target documents
accordingly.

## Evidence Basis

The "publishable first version" stance is only valid while these repository
facts remain true:

- The project exposes runnable CLI and MCP entry points: `semantic-guard` and
  `semantic-guard-mcp`.
- The repository includes README material, JSON Schema, fixture records, unit
  tests, a `doctor` command, and a companion Codex skill bundle.
- The package build includes schemas, convention docs, fixtures, and
  `skills/semantic-implementation`.
- Public wording keeps the research-prototype, local-fixture, heuristic-check,
  and human-final-decision limits visible.

Live checks used when drafting this plan:

- GitHub `main` resolved to `f3b2d527a844817277ec88ed639a5e1bdfb74ce8`.
- Remote `README.md` and `README.ja.md` contained the agentic revision-loop
  positioning.
- Local `README.md` and `README.ja.md` were older than that remote positioning.
- CORE staging under
  `<CORE-publication-staging-source>`
  was also older than that remote positioning.

## Accepted Public Framing

Use this short Japanese wording for self-introductions, README summaries, and
portfolio material:

```text
公開可能な初版としては完成済みです。現在は、監査性能、適用範囲、AIエージェントの修正ループへの接続を継続的に改善しています。
```

The longer wording is:

```text
Criterion Loom は、Codex 等の AI エージェント作業に対し、依頼、計画、変更説明、完了主張の曖昧さや不足を JSON の監査結果として返す、公開可能な初版として完成しています。

現在は、実働する CLI / MCP server / companion skill、JSON Schema、fixture、doctor command、公開文書を備えた状態です。一方で、一般文書を完全に理解する完成済み要求工学製品ではなく、語彙規則と軽量な構造検査に基づく研究試作です。

今後は、監査性能の改善、過警告や見逃しの低減、fixture / corpus の拡充、AI エージェントの修正ループへの戻し方の改善を進めています。
```

## Boundaries

Keep these limits explicit whenever the public-v0.1 claim is used:

- Public v0.1 means "publishable first version", not "finished requirements engineering product".
- Performance means audit performance: better findings, fewer false positives, fewer misses, better coverage, and better revision-loop usability.
- It does not approve AI output as correct.
- It does not replace human `accept`, `request_revision`, or `defer` decisions.
- It does not prove general natural-language understanding accuracy.
- Fixture evaluation is local regression coverage, not general precision or recall.
- `trace-report` and vocabulary matching are lightweight trace aids, not causal proof or durable project management.

## Repository Changes To Make

### P0: Align Public Positioning

Update the main public documents so they all carry the same state:

- `README.md`
  - Say Criterion Loom is a meaning-first audit CLI / MCP server / companion Codex skill.
  - Say public v0.1 is ready as a publishable first version.
  - Say audit output feeds an agentic revision loop before final human review.
  - Say future work is audit-performance improvement, not basic completion.
- `README.ja.md`
  - Add the Japanese completion wording above.
  - Keep the research-prototype and human-final-decision boundaries.
  - Include the agent-side correction loop: request framing, plans, change explanations, verification, and finish claims.
- `docs/agent-revision-loop-positioning-2026-06-30.md`
  - Keep as the positioning source for outward wording if it is meant to be public.
  - If it is not meant to be public, remove it from public documentation maps and keep it as private history.
- `docs/acceptance-review-bundle.md`
  - State that intermediate audits first return to Codex for correction, additional verification, or re-presentation.
  - Keep final human decision separate and pending until a person decides.
- `skills/semantic-implementation/README.md`
  - State that audit output should return to the Codex work loop.
  - Keep the skill as orchestration, not the deterministic audit core.
- `skills/semantic-implementation/SKILL.md`
  - Preserve the existing rule that reviewer output is supplement material.
  - Make sure "revise based on findings" does not become "auto-approve based on findings".

### P0: Reconcile Repository Truth

Current observed state on 2026-06-30:

- GitHub `main` at `f3b2d527a844817277ec88ed639a5e1bdfb74ce8` already contains newer README positioning for the agentic revision loop.
- Local `<local-semantic-guard-checkout>` contains `docs/agent-revision-loop-positioning-2026-06-30.md`, but its `README.md` and `README.ja.md` are older than GitHub `main`.
- CORE staging under `<CORE-publication-staging-source>` is also older than GitHub `main`.

Choose one source of truth before editing further:

1. Treat GitHub `main` as canonical and refresh local plus CORE staging from it.
2. Treat local working files as canonical and deliberately re-apply only selected GitHub changes.

The first option is currently safer because GitHub already contains the public
revision-loop language that the new positioning document describes.

### P1: Update Public Documentation Map

Check `docs/README.md` after reconciliation:

- If `agent-revision-loop-positioning-2026-06-30.md` is public, keep it listed.
- If it is private working history, remove it from the public-facing set.
- Make sure the map does not point to missing public files.
- If `CODE_OF_CONDUCT.md`, `SUPPORT.md`, `docs/release/publication-format.md`, or
  `docs/release/public-repository-readiness.md` are part of the public repo,
  ensure local and CORE staging include them too.

### P1: Update Portfolio And Evidence Documents

Update Japanese outward-facing material to use the new completion stance:

- `docs/ja/company-evidence.md`
  - Present Criterion Loom as a completed public first version.
  - Say performance improvement is ongoing.
  - Avoid saying it is an unfinished tool in a way that weakens the current claim.
- `docs/ja/quickstart.md`
  - Keep commands runnable after the package and skill-bundle changes.
- Any self-PR or成果説明 draft
  - Use "完成済みの初版、改善中の監査性能".

### P1: Sync CORE Publication Staging

After repository text is reconciled:

1. Copy the updated public source into
   `<CORE-publication-staging-source>`.
2. Preserve the skill bundle inclusion in `pyproject.toml`.
3. Rebuild wheel and sdist into the staging `dist/`.
4. Update `STAGING-NOTES.md` with:
   - public v0.1 completion wording,
   - agent revision-loop positioning,
   - audit-performance improvement as ongoing work,
   - verification command results.
5. Remove generated files from staging source:
   - `.git`
   - `.venv`
   - `.backups`
   - `__pycache__`
   - `*.pyc`
   - `.DS_Store`

### P2: Improve Audit Performance

Track performance improvement as ongoing work, not as a blocker for public v0.1:

- Expand fixtures and field corpus for real examples.
- Separate true over-warning from useful strictness.
- Add regression rows for current false positives and false negatives.
- Improve Japanese synonym and heading recognition where examples show misses.
- Improve `trace-report` tag handling and vocabulary profile examples.
- Strengthen `audit-decision-state` handoff examples for unresolved decisions.
- Improve reviewer-routing pressure examples without letting reviewer output decide acceptance.
- Keep score semantics clear: score is a deterministic signal, not a quality probability.

## Verification Before Calling The Repository Updated

Run these from the repository root after changes:

```sh
uv run --python 3.13 --project . python -m compileall src/semantic_guard tests
uv run --python 3.13 --project . python -m unittest discover -s tests
uv run --python 3.13 --project . semantic-guard evaluate-fixtures
uv run --python 3.13 --project . semantic-guard doctor
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.md
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file README.ja.md
uv run --python 3.13 --project . semantic-guard audit-request --kind document --file docs/agent-revision-loop-positioning-2026-06-30.md
```

For CORE staging, additionally verify:

```sh
uv build --out-dir <CORE-publication-staging-dist>
uv run --python 3.13 --with <CORE-publication-staging-dist>/semantic_guard-0.1.0-py3-none-any.whl --no-project python - <<'PY'
from pathlib import Path
import semantic_guard

skill_dir = Path(semantic_guard.__file__).resolve().parents[1] / "skills" / "semantic-implementation"
assert (skill_dir / "SKILL.md").is_file()
assert (skill_dir / "README.md").is_file()
print(skill_dir)
PY
```

## Close Criteria

Repository-side update can be closed when:

- Public README, Japanese README, companion skill docs, and acceptance-bundle docs all use the same completion stance.
- GitHub, local working tree, and CORE staging no longer disagree about the public positioning.
- The package archives still include schemas, fixtures, convention docs, and the companion skill bundle.
- The verification commands pass.
- The public wording says "publishable first version" and "audit-performance improvement", without claiming final correctness, automatic approval, or general NLU accuracy.
