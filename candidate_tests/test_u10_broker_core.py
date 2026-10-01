from __future__ import annotations

import copy
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from semantic_guard_u10_broker.core import (
    _sign_statement,
    _verify_statement_signature,
    validate_execution_request_v1,
)
from semantic_guard_u10_broker.protected_io import BrokerBoundaryError


class U10BrokerCoreTests(unittest.TestCase):
    def test_public_request_denominator_is_exactly_three_caller_fields(self) -> None:
        request = {
            "entry_id": "u10.entry.local",
            "command_id": "verify.u10.containment-smoke",
            "request_nonce": "a" * 64,
        }
        validate_execution_request_v1(request)
        forbidden = {
            "source_path": "/tmp/source",
            "expected_source_digest": {"algorithm": "sha256", "value": "0" * 64},
            "eligibility_service": "fake",
            "output_directory": "/tmp/output",
            "receipt_id": "caller.receipt",
            "execution_uid": 501,
            "argv": ["/bin/true"],
        }
        for name, value in forbidden.items():
            with self.subTest(name=name):
                changed = {**request, name: value}
                with self.assertRaises(BrokerBoundaryError):
                    validate_execution_request_v1(changed)

    def test_signature_binds_the_complete_statement_and_domain(self) -> None:
        key = Ed25519PrivateKey.generate()
        statement = {
            "envelope_id": "envelope.u10.test",
            "request_nonce": "b" * 64,
            "authority": "occurrence_only",
        }
        signature = _sign_statement(statement, key)
        _verify_statement_signature(statement, signature, key.public_key())

        changed = copy.deepcopy(statement)
        changed["authority"] = "positive_assurance"
        with self.assertRaises(BrokerBoundaryError):
            _verify_statement_signature(changed, signature, key.public_key())


if __name__ == "__main__":
    unittest.main()
