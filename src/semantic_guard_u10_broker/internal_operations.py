"""Explicit package-internal operation seam for trusted U-10 callers.

This module is not a public broker API.  It centralizes the small set of
operations currently shared across ``core``, ``supervisor``, and fixed control
scripts so those callers do not each depend on arbitrary private ``core``
symbols.  Implementations remain in ``core`` for compatibility until they can
be moved with artifact-bound regression evidence.

Pre-import outer launchers must not import this module.
"""

from __future__ import annotations

from .core import (
    _build_signed_envelope_v3 as build_signed_envelope_v3,
    _load_current_store_activation_context_v1 as load_current_store_activation_context_v1,
    _require_time_order as require_time_order,
    _revocation_transition_ref_v1 as revocation_transition_ref_v1,
    _store_transition_ref_v1 as store_transition_ref_v1,
    _validate_publisher_contract_binding_v1 as validate_publisher_contract_binding_v1,
)


__all__ = [
    "build_signed_envelope_v3",
    "load_current_store_activation_context_v1",
    "require_time_order",
    "revocation_transition_ref_v1",
    "store_transition_ref_v1",
    "validate_publisher_contract_binding_v1",
]
