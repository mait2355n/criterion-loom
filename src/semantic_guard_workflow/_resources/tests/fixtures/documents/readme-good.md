# Local Audit Helper

## Overview

This document describes a local CLI audit helper for Codex work.

## Status

The helper is a prototype. It is not a release gate.

## When To Use

Use it when a reader needs enough context to run a document audit and inspect the JSON result.

## CLI

Run this command to inspect document audit output:

```sh
semantic-guard audit-request --kind document --file README.md
```

## Output Shape

The command returns status, score, findings, missing, next_actions, and details.

## Limitations

It is heuristic and does not replace human review.
