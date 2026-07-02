# Security Policy

Criterion Loom's `semantic-guard` implementation is not a security scanner. It may warn when a diff appears to touch sensitive surfaces, but it does not prove that code is safe.

## Purpose

This policy defines how to report repository safety issues without exposing private data, and it clarifies that `semantic-guard` does not provide vulnerability coverage for arbitrary projects.

## Audience And Use

Use this file if you believe the repository, package, CLI, MCP server, examples, or documentation expose a sensitive boundary. Do not use it as a request for broad codebase security certification.

## Reporting Security Issues

Do not paste secrets, private prompts, customer data, tokens, or unredacted proprietary examples into public issues.

If GitHub private vulnerability reporting is enabled for the repository, use it. Otherwise, open a minimal public issue that describes the affected component and impact without sensitive details, and state that private details are available through an appropriate channel.

Example public report shape:

```text
Component: semantic-guard CLI
Impact: sensitive value can appear in an error message
Sensitive details: withheld from public issue
Verification: reproduced with redacted local input
```

## Report Contract

A useful report names the affected component, expected boundary, observed behavior, impact, and whether the example was redacted. It should not include secrets or unredacted private material.

## Supported Versions

This public snapshot is a publishable v0.1 deterministic heuristic tool. Until versioned releases exist, security fixes and sensitive-boundary corrections are handled on the current public branch.

## Scope

In scope:

- accidental secret exposure in repository files.
- unsafe defaults in the CLI or MCP server.
- vulnerabilities in project code or packaging.
- examples that encourage unsafe disclosure of private data.

Out of scope:

- claims that `semantic-guard` failed to detect an arbitrary vulnerability.
- broad requests to certify a codebase's security posture.
- unredacted private data submitted as test material.
