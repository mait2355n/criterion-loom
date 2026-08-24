# Security Policy

## Supported line

Security fixes are considered for the canonical `1.x` line. The publication-repaired `legacy/semantic-guard-v0.1.0/` archive is retained for historical and explicit compatibility use and does not receive routine fixes. Its manifest identifies the original Git anchor and the disclosed publication repair.

## Reporting a vulnerability

If the repository's Security tab shows **Report a vulnerability**, use that
GitHub private vulnerability-reporting form.

If that private form is not available, [open the issue
chooser](https://github.com/mait2355n/criterion-loom/issues/new/choose) and
select **Sensitive contact request**. That fallback creates a public issue; it
does not make the submitted text private. Provide only the broad report kind,
the affected public surface, a minimal non-sensitive summary, and confirmation
that private follow-up is needed.

Never place credentials, tokens, private or proprietary documents, personal
information, exploit or abuse details, reproduction steps, logs, private
endpoints, or other sensitive material in the public contact request. Use the
request only to ask maintainers for an available private follow-up route.

After an appropriate private route has been established, provide the affected
version, entry point, prerequisites, minimal reproduction, expected impact, and
whether secrets or external systems were involved. Continue to redact anything
not needed for triage.

No response-time or remediation-time service level is promised. A report is evidence for triage, not proof that a vulnerability exists or has been resolved.

## Security boundary

`semantic-guard` is not a vulnerability scanner, malware sandbox, identity verifier, signature service, or security certification system. Its `secure-operation` contract checks the internal consistency of supplied operation records within a declared boundary; it does not verify external identity, trusted time, cryptographic signatures, or real-world action authenticity.

MCP legacy shadow comparison is disabled unless an operator explicitly enables it and supplies a controlled external legacy root. Tool callers must not be allowed to choose arbitrary executables or filesystem roots.

Run package verification only against trusted local wheels. Installing or importing a wheel executes package code; the verifier is not an operating-system sandbox.
