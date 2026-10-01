"""Fail-closed Darwin extended-ACL detection for U-10 protected paths."""

from __future__ import annotations

import ctypes
import errno
import os
from pathlib import Path
import sys


ACL_TYPE_EXTENDED = 0x00000100


def assert_no_extended_acl(path: Path) -> None:
    """Reject every Darwin extended ACL; POSIX mode remains a separate check.

    Darwin reports an absent extended ACL as ``NULL`` with ``ENOENT`` even
    when the filesystem object exists.  Any other failure is unresolved and
    therefore rejected.  ``acl_get_link_np`` avoids following a final symlink.
    """

    if sys.platform != "darwin":
        return
    libc = ctypes.CDLL(None, use_errno=True)
    acl_get_link = libc.acl_get_link_np
    acl_get_link.argtypes = [ctypes.c_char_p, ctypes.c_int]
    acl_get_link.restype = ctypes.c_void_p
    acl_free = libc.acl_free
    acl_free.argtypes = [ctypes.c_void_p]
    acl_free.restype = ctypes.c_int
    ctypes.set_errno(0)
    acl = acl_get_link(os.fsencode(path), ACL_TYPE_EXTENDED)
    if acl:
        try:
            raise PermissionError(errno.EACCES, "extended ACL prohibited", path)
        finally:
            acl_free(acl)
    observed_errno = ctypes.get_errno()
    if observed_errno != errno.ENOENT:
        raise OSError(observed_errno, os.strerror(observed_errno), path)


__all__ = ["assert_no_extended_acl"]
