from __future__ import annotations

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent


def resource_path(*parts: str) -> Path:
    """Resolve a repo resource in source checkouts and installed wheels."""
    relative = Path(*parts)
    candidates = [
        PACKAGE_ROOT.parents[1] / relative,  # source layout: <repo>/src/semantic_guard
        PACKAGE_ROOT.parents[0] / relative,  # wheel layout: <site-packages>/semantic_guard
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]
