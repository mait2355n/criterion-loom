"""Resolve bundled JSON Schemas in source trees and installed distributions."""

from __future__ import annotations

from pathlib import Path


def schema_directory(*, sentinel: str = "common.schema.json") -> Path:
    """Return the closed schema directory without depending on repository layout.

    Wheels install schemas below ``semantic_guard/schemas`` while the
    canonical source tree keeps them at ``schemas``.  Callers must not silently
    fall back to an arbitrary current-working-directory path.
    """

    here = Path(__file__).resolve()
    packaged = here.parent / "schemas"
    if (packaged / sentinel).is_file():
        return packaged

    source_root = here.parents[2]
    source = source_root / "schemas"
    source_package = source_root / "src" / "semantic_guard"
    if (
        (source_root / "pyproject.toml").is_file()
        and source_package.resolve() == here.parent
        and (source / sentinel).is_file()
    ):
        return source
    raise FileNotFoundError(
        f"semantic-guard v1 schemas are unavailable; missing {sentinel!r} "
        "from both packaged and source layouts"
    )


def schema_path(name: str) -> Path:
    """Resolve one known schema filename below the trusted schema directory."""

    if not name or name != Path(name).name or not name.endswith(".schema.json"):
        raise ValueError(f"invalid schema filename: {name!r}")
    path = schema_directory(sentinel=name) / name
    if not path.is_file():
        raise FileNotFoundError(f"semantic-guard v1 schema is unavailable: {name}")
    return path


__all__ = ["schema_directory", "schema_path"]
