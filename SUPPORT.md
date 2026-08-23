# Support

## Start here

```sh
uv sync --locked
uv run --locked semantic-guard --help
uv run --locked semantic-guard schema audit-result
uv run --locked semantic-guard schema direction-binding-audit
```

The 1.1.0 source contract has four CLI commands—`audit-requirement`, `audit-direction-binding`, `shadow-compare`, and `schema`—and four matching MCP tools. Its closed schema registry contains 24 names. Former 0.1.0 commands are available only in the frozen legacy source and are not aliases of the v1 implementation. A selected local 1.1.0 wheel and sdist have passed the packaged-contract checks summarized in `docs/implementation-status.md`; still verify the exact installed artifact because that result does not identify every build or published package.

## Asking for help

Use a GitHub issue for reproducible usage, documentation, packaging, or rule-gap reports. Use the private process in `SECURITY.md` for suspected vulnerabilities.

Include:

- `semantic-guard` version and installation method;
- operating system and Python version;
- exact command and exit code;
- redacted standard output and standard error;
- smallest non-sensitive input that reproduces the problem;
- whether optional morphology or dependency providers were installed;
- whether the result came from canonical v1 or the frozen 0.1.0 implementation.

Do not attach secrets, proprietary requirements, personal information, tokens, or an uncontrolled legacy execution environment.

## Interpretation support

A `pass`, `warn`, or `block` value is a workflow disposition under the selected versioned policy. It is not a correctness probability, human acceptance, production approval, or security finding.

For migration and compatibility questions, read `docs/migration-v0.1.0-to-v1.0.0.md`. For direction-binding semantics and limits, read `docs/direction-binding-audit.md`. For current limitations, read `docs/implementation-status.md`. The historical 1.0.0 canonicalization audit is `docs/audits/canonicalization-audit-v1.0.0-2026-07-17.md`.

No response-time, repair-time, or long-term maintenance service level is promised.
