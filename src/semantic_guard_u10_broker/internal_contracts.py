"""Package-side U-10 control contracts shared after trust establishment.

The stdlib-only outer launchers deliberately keep independent copies of these
values because they run before the broker package is trusted and importable.
Contract tests must keep those pre-import mirrors and the JSON schemas equal to
this package-side source.
"""

from __future__ import annotations


CONTROL_ALLOWED_OPERATIONS_V1 = (
    "activate-snapshot",
    "activate-store",
    "key",
    "project-snapshot",
    "revoke-store",
)

STORE_ACTIVATION_LEDGER_POLICY_V3 = (
    "authorization_id_interval_receipt_atomic_publish/v3"
)
STORE_REVOCATION_LEDGER_POLICY_V2 = (
    "authorization_id_interval_receipt_atomic_publish/v2"
)
STORE_LEDGER_RETENTION_POLICY_V1 = (
    "no_automatic_deletion_while_store_revision_is_retained/v1"
)


__all__ = [
    "CONTROL_ALLOWED_OPERATIONS_V1",
    "STORE_ACTIVATION_LEDGER_POLICY_V3",
    "STORE_LEDGER_RETENTION_POLICY_V1",
    "STORE_REVOCATION_LEDGER_POLICY_V2",
]
