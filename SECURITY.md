# Security Policy

## Supported line

Security fixes are considered for the canonical `1.x` line. The frozen `legacy/semantic-guard-v0.1.0/` source is retained for historical and explicit compatibility use and does not receive routine fixes.

## Reporting a vulnerability

Use GitHub's private vulnerability-reporting channel when available. If it is unavailable, contact the repository owner through a private channel before opening a public issue.

Include the affected version, entry point, prerequisites, minimal reproduction, expected impact, and whether secrets or external systems were involved. Do not place credentials, tokens, private documents, exploit material, or personal information in a public issue.

No response-time or remediation-time service level is promised. A report is evidence for triage, not proof that a vulnerability exists or has been resolved.

## Security boundary

`semantic-guard` is not a vulnerability scanner, malware sandbox, identity verifier, signature service, or security certification system. Its `secure-operation` contract checks the internal consistency of supplied operation records within a declared boundary; it does not verify external identity, trusted time, cryptographic signatures, or real-world action authenticity.

MCP legacy shadow comparison is disabled unless an operator explicitly enables it and supplies a controlled external legacy root. Tool callers must not be allowed to choose arbitrary executables or filesystem roots.

Run package verification only against trusted local wheels. Installing or importing a wheel executes package code; the verifier is not an operating-system sandbox.
