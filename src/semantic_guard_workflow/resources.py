"""Resolve workflow-owned resources identically in checkouts and distributions."""

from __future__ import annotations

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent


def resource_path(*parts: str) -> Path:
    """Return an owned resource path without using canonical or adjacent data.

    Missing files remain missing. Source trees and wheels carry the same
    ``_resources`` layout, so neither a current directory nor project metadata
    can redirect lookup into the canonical package or an unrelated checkout.
    """
    relative = Path(*parts)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("workflow resources require a relative path without '..'")
    return PACKAGE_ROOT / "_resources" / relative
