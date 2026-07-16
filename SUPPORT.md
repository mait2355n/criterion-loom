# Support

## Start here

```sh
uv sync --locked
uv run --locked semantic-guard --help
uv run --locked semantic-guard schema audit-result
```

The canonical v1 CLI has three commands: `audit-requirement`, `shadow-compare`, and `schema`. Former 0.1.0 commands are available only in the frozen legacy source and are not aliases of the v1 implementation.

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

For migration and compatibility questions, read `docs/migration-v0.1.0-to-v1.0.0.md`. For current limitations, read `docs/implementation-status.md` and `docs/canonicalization-audit.md`.

No response-time, repair-time, or long-term maintenance service level is promised.
