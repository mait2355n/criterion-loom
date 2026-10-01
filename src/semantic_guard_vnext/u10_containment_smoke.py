"""Two exact U-10 smoke tests loaded as an isolated, digest-bound file."""

from __future__ import annotations

import errno
import os
import subprocess
import sys
import unittest


class U10ContainmentSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        # The governed runner must execute this file directly. Importing it by
        # its repository package name would execute semantic_guard_vnext's
        # broad initializer before this smoke denominator is loaded.
        self.assertNotIn("semantic_guard_vnext", sys.modules)

    def test_subprocess_creation_is_denied_by_kernel_policy(self) -> None:
        with self.assertRaises(OSError) as raised:
            subprocess.run(
                ["/usr/bin/true"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                env={"PATH": ""},
            )
        self.assertIn(raised.exception.errno, {errno.EPERM, errno.EACCES})

    @unittest.skipUnless(hasattr(os, "fork"), "fork is unavailable")
    def test_direct_fork_is_denied_by_kernel_policy(self) -> None:
        with self.assertRaises(OSError) as raised:
            os.fork()
        self.assertIn(raised.exception.errno, {errno.EPERM, errno.EACCES})


if __name__ == "__main__":
    unittest.main()
