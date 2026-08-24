# Security Policy

> **Historical boundary (0.1.0 publication-repaired archive).** This document
> describes the predecessor as recorded for the 0.1.0 line; it is not current 1.x
> state or operating guidance. Original-byte authority: tag `v0.1.0`, commit
> `e0a3dd39f17385b66f6361ade25eb44bed6e1ab3`.

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

At the 0.1.0 record point, this public snapshot was a research prototype. Before versioned releases existed, security fixes and sensitive-boundary corrections were handled on the then-current public branch.

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
