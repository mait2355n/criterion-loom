# Secure-operation v1 audit boundary

`secure-operation/v1` audits the internal consistency of supplied
information-handling declarations. It deliberately does not produce a strong
security, policy-adoption, evidence-authenticity, or nonapplicability proof.

The historical route names `adopted_profile` and
`verified_nonapplicability` identify the two input contracts. They are not
result claims. Version 1 emits only:

- `declared_profile_internally_consistent`;
- `declared_nonapplicability_internally_consistent`;
- `reactivated`; or
- `not_established`.

Every result also contains `unproved_claim_codes`. In this version they state
that external human-decision authenticity, independent-review authenticity,
operational-evidence authenticity, denominator authenticity, scope-version
continuity, and trusted-time authenticity remain unproved. The removed v0
statuses `profile_controls_satisfied` and
`verified_nonapplicable_for_declared_local_scope` are schema-invalid.

The version map is intentionally mixed and must be read per record rather
than inferred from the outer envelope:

- assessment envelope: `secure-operation/v1`;
- scope manifest: `secure-operation-scope-manifest/v1`;
- evidence observation: `secure-operation-evidence/v1`;
- adopted-path profile: `secure-operation-profile/v0`;
- nonapplicability-path profile: `secure-operation-nonapplicability-profile/v0`;
- independent-review record: `secure-operation-independent-review/v1`.

The two profile records remain v0 because this change strengthened the v1
assessment, evidence, review, and replay boundary without silently renaming
the inner profile contracts. A future incompatible profile-shape change must
version those records independently.

## Authority boundary

semantic-guard may validate schema closure, replay digests, compare declared
scope with typed records, derive local conditions, and compute a reproducible
internal-consistency result. It does not:

- adopt, retire, or amend an information-handling policy;
- verify an external signature, identity, clock, inventory, or evidence store;
- determine the true classification of real material;
- issue or rotate credentials;
- transmit data;
- declare an incident or send a notification;
- accept operational risk; or
- make final human acceptance.

`authority_boundary.verify_external_authenticity` and
`authority_boundary.strong_positive_claims_enabled` are therefore both
`false`. Plain SHA-256 digests detect inconsistent replay inside the supplied
bundle; a submitter can recompute them, so they are not authenticity evidence.

## Declared human decisions

A decision binds all of:

- profile identifier and version;
- exact profile-basis digest;
- exact scope digest;
- decision sequence and decision time; and
- the declared external record reference.

For the same profile basis and scope, the latest unique sequence is effective.
A later retirement overrides an earlier adoption. Same-sequence conflicts,
sequence/time disagreement, a stale decision pointer, or a decision over a
different scope is rejected.

`authenticity_status` is fixed to `unverified`. The decision builder records
supplied material; it does not verify a human signature. A future version needs
an external verifier receipt before any strong adoption claim can exist.

## Declared denominator

Exactly one subject, configuration, and runtime-path manifest is required.
Each manifest now binds:

- a declared inventory authority reference;
- non-empty `scope_inventory` evidence references;
- a closure rule;
- an optional predecessor-manifest digest; and
- the complete entry set used by this assessment.

Inventory evidence must name the manifest, use `scope_inventory`, match the
declared inventory-authority identity, be current, and bind the complete scope
digest. Every runtime entry maps to exactly one flow component; every subject
entry maps to data material; every declared flow has exactly one observation.

This closes the supplied denominator, not the real system. Version 1 has no
authoritative inventory resolver and therefore always reports
`scope_denominator_authenticity_unproved` and
`scope_version_continuity_unproved`. Omitted real paths still require an
external discovery process and must be recorded as unresolved when known.

## Evidence contracts

`trust_class`, observer kind, and observer relationship are checked as a tuple:

- `self_reported` requires `self` and cannot support a positive internal result;
- `tool_observed` requires a tool observer relationship;
- `independently_observed` requires an independent relationship; and
- `signed` requires an independent human or external-system observer, while
  remaining cryptographically unverified in v1.

Relabelling a self observer as `tool_observed` is an integrity error.

Claim-specific evidence kinds are enforced:

- information flows use `information_flow_observation`;
- dependency, resource, denial-of-service, incident, and notification controls
  use their corresponding typed evidence;
- requalification triggers use every kind required by their adopted profile;
- boundary conditions use scope or runtime observations according to the
  condition;
- restart claims use `restart_test`;
- retention uses `retention_test` and, when required, `deletion_test`; and
- independent review uses `independent_review` from the exact reviewer identity.

Evidence freshness requires trusted declared time, observation before
assessment, unexpired evidence, and profile maximum age. These checks do not
authenticate the clock; that limitation remains explicit.

## Declared-profile path

The profile binds purposes, destinations, data classes, minimization,
redaction, transport and at-rest encryption declarations, credentials,
least-privilege scopes, operational controls, requalification triggers, and
retention rules.

Every persistent component requires a typed retention observation bound to the
exact component and retention-rule digest. The configured maximum must not
exceed the rule. When deletion evidence is required, both the boolean result
and a `deletion_test` observation are mandatory. Missing retention observation,
an excessive configured duration, or missing deletion evidence prevents
`declared_profile_internally_consistent`.

The result also remains `not_established` for missing or mismatched effective
decision, missing declared independent review, untrusted/stale evidence,
unresolved blocking scope, unapproved flow purpose/class/destination/field,
unproved minimization or required encryption, secret logging, failed controls,
or observed/unresolved requalification triggers.

## Declared-nonapplicability path

The six conditions are not accepted from stored `confirmed` flags. They are
derived from the bound manifests:

1. every data class and source is synthetic/local-fixture material;
2. every execution location is local;
3. no privilege or credential is present;
4. no durable output, log, or artifact is present;
5. no external provider exists; and
6. no sensitive class exists.

A `confirmed` condition contradicting the derived scope is an integrity error.
Public-class material therefore cannot be laundered into “synthetic only.”

The restart record must bind the before and after configuration and runtime
manifest digests to the current declared scope. A before/after difference,
failed status, or post-restart mismatch causes `reactivated`. The restart record
itself, not only its cited evidence, must also satisfy profile maximum age.

External execution, real material, durable output, sensitive material,
privilege, production scope, or restart mismatch automatically reactivates the
profile path. Any unresolved scope prevents declared nonapplicability.

## Resource bounds and external effects

Schema and semantic validation cap scope entries, components, flows, evidence,
and relevant strings. Flow closure uses an iterative topological evaluation;
deep valid graphs no longer depend on Python recursion depth. Oversized input
fails with `input_resource_limit_exceeded` before full replay.

The module reads its local JSON Schema and otherwise performs only in-memory
copying, hashing, comparison, and validation. It performs no network request,
subprocess invocation, file write, credential operation, transmission,
notification, incident action, or policy action.

## Verification corpus

`tests/test_secure_operation.py` covers deterministic weak results and hostile
cases for:

- latest retirement and same-sequence conflicts;
- exact basis-and-scope decision binding;
- legacy strong-status rejection;
- self-observer trust laundering;
- public-to-synthetic condition laundering;
- claim-specific evidence kinds and reviewer identity;
- denominator authority binding;
- restart before/after mismatch and restart-record age;
- retention and deletion evidence;
- deep flow graphs and collection limits;
- flow, component, classification, destination, policy, unresolved-scope, and
  automatic-reactivation integrity; and
- digest and deterministic-result replay.

These tests establish local contract behaviour only. External authenticity,
field validity, real inventory completeness, operational effectiveness, and
final human acceptance remain outside their proof boundary.
