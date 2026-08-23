"""Canonical semantic-guard release identity.

Keep this value aligned with ``project.version`` in ``pyproject.toml``.  The
packaged-contract verifier checks the source, distribution metadata, CLI, and
audit producer provenance together so a release cannot silently drift.
"""

from __future__ import annotations


__version__ = "1.1.0"


__all__ = ["__version__"]
