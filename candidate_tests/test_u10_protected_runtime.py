from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from semantic_guard_u10_broker.protected_io import (
    BrokerBoundaryError,
    read_protected_file,
    reserve_nonce_once,
    validate_protected_tree,
)


class U10ProtectedRuntimeTests(unittest.TestCase):
    def _protected_root(self, temporary: str) -> Path:
        root = Path(temporary) / "protected"
        root.mkdir(mode=0o700)
        return root

    def test_protected_read_binds_owner_mode_and_regular_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._protected_root(temporary)
            artifact = root / "artifact.json"
            artifact.write_bytes(b"{}\n")
            artifact.chmod(0o600)
            self.assertEqual(
                read_protected_file(
                    artifact,
                    protected_root=root,
                    required_uid=os.getuid(),
                    private=True,
                ),
                b"{}\n",
            )

    def test_symlink_and_group_writable_material_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._protected_root(temporary)
            target = root / "target"
            target.write_text("target", encoding="utf-8")
            target.chmod(0o600)
            link = root / "link"
            link.symlink_to(target)
            with self.assertRaises(BrokerBoundaryError):
                read_protected_file(
                    link,
                    protected_root=root,
                    required_uid=os.getuid(),
                )

            target.chmod(0o620)
            with self.assertRaises(BrokerBoundaryError):
                read_protected_file(
                    target,
                    protected_root=root,
                    required_uid=os.getuid(),
                )

    def test_private_key_material_must_not_be_group_or_world_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._protected_root(temporary)
            key = root / "key.pem"
            key.write_text("secret", encoding="utf-8")
            key.chmod(0o644)
            with self.assertRaises(BrokerBoundaryError):
                read_protected_file(
                    key,
                    protected_root=root,
                    required_uid=os.getuid(),
                    private=True,
                )

    def test_nonce_is_consumed_before_work_and_cannot_be_replayed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            ledger = self._protected_root(temporary)
            nonce = "a" * 64
            first, record = reserve_nonce_once(
                {
                    "entry_id": "entry.u10.local",
                    "command_id": "verify.u10.smoke",
                    "request_nonce": nonce,
                },
                ledger_root=ledger,
                required_uid=os.getuid(),
            )
            self.assertTrue(first.is_file())
            self.assertEqual(record["state"], "consumed_before_launch")
            with self.assertRaises(BrokerBoundaryError) as observed:
                reserve_nonce_once(
                    {
                        "entry_id": "entry.u10.local",
                        "command_id": "verify.u10.smoke",
                        "request_nonce": nonce,
                    },
                    ledger_root=ledger,
                    required_uid=os.getuid(),
                )
            self.assertEqual(observed.exception.code, "request_nonce_replay")

    def test_protected_tree_rejects_hardlinks_and_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._protected_root(temporary)
            artifact = root / "artifact"
            artifact.write_text("fixed", encoding="utf-8")
            artifact.chmod(0o400)
            validate_protected_tree(root, required_uid=os.getuid())

            linked = root / "linked"
            os.link(artifact, linked)
            with self.assertRaises(BrokerBoundaryError):
                validate_protected_tree(root, required_uid=os.getuid())

    @unittest.skipUnless(sys.platform == "darwin", "Darwin ACL contract")
    def test_extended_acl_is_rejected_even_when_posix_mode_is_private(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._protected_root(temporary)
            artifact = root / "artifact"
            artifact.write_text("fixed", encoding="utf-8")
            artifact.chmod(0o600)
            subprocess.run(
                ["/bin/chmod", "+a", "everyone allow add_file", str(root)],
                check=True,
            )
            try:
                with self.assertRaises(BrokerBoundaryError) as observed:
                    read_protected_file(
                        artifact,
                        protected_root=root,
                        required_uid=os.getuid(),
                    )
                self.assertEqual(
                    observed.exception.code, "protected_path_extended_acl"
                )
            finally:
                subprocess.run(["/bin/chmod", "-N", str(root)], check=True)


if __name__ == "__main__":
    unittest.main()
