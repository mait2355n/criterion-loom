"""Resolve bundled JSON Schemas in source trees and installed distributions."""

from __future__ import annotations

from pathlib import Path


def schema_directory(*, sentinel: str = "common.schema.json") -> Path:
    """Resolve only this candidate package's closed schema directory.

    Source checkouts and wheels carry the same package-local resources. The
    canonical v1 repository's schemas are a separate contract and cannot be a
    fallback when candidate resources are absent.
    """

    here = Path(__file__).resolve()
    packaged = here.parent / "schemas"
    if (packaged / sentinel).is_file():
        return packaged

    raise FileNotFoundError(
        f"semantic-guard vNext schemas are unavailable; missing {sentinel!r} "
        "from the candidate package"
    )


def schema_path(name: str) -> Path:
    """Resolve one known schema filename below the trusted schema directory."""

    if not name or name != Path(name).name or not name.endswith(".schema.json"):
        raise ValueError(f"invalid schema filename: {name!r}")
    path = schema_directory(sentinel=name) / name
    if not path.is_file():
        raise FileNotFoundError(f"semantic-guard vNext schema is unavailable: {name}")
    return path


__all__ = ["schema_directory", "schema_path"]
