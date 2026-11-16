"""A JSON Schema validator whose ``pattern`` matches the whole string.

``jsonschema`` checks ``pattern`` with ``re.search``. In Python ``$`` also matches
just before a final newline, so a value such as ``"sha256:abc\n"`` satisfies a
pattern written ``^sha256:[0-9a-f]+$`` although the schema author meant a value
with no trailing newline. In ECMA-262 (the dialect JSON Schema specifies) ``$``
matches only at the end of the input. This validator restores that meaning
without editing any published schema: every unescaped ``$`` outside a character
class is read as the end of the string.

The module is copied verbatim into each package namespace so that none of them
depends on another; a test keeps the copies identical.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import datetime
from functools import lru_cache
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, ValidationError, validators


@lru_cache(maxsize=4096)
def strict_pattern_text(pattern: str) -> str:
    """Return ``pattern`` with each unescaped ``$`` outside a class read as end of string."""
    out: list[str] = []
    index = 0
    in_class = False
    while index < len(pattern):
        char = pattern[index]
        if char == "\\":
            out.append(pattern[index:index + 2])
            index += 2
            continue
        if in_class:
            if char == "]":
                in_class = False
            out.append(char)
        elif char == "[":
            in_class = True
            out.append(char)
            # A leading "]" or "^]" is a literal member of the class.
            if pattern[index + 1:index + 2] == "^":
                out.append("^")
                index += 1
            if pattern[index + 1:index + 2] == "]":
                out.append("]")
                index += 1
        elif char == "$":
            out.append(r"\Z")
        else:
            out.append(char)
        index += 1
    return "".join(out)


def matches_pattern(pattern: str, instance: str) -> bool:
    """Whether ``instance`` satisfies ``pattern`` with ECMA-262 end-of-input semantics."""
    return re.search(strict_pattern_text(pattern), instance) is not None


def _pattern(validator: Any, pattern: str, instance: Any, schema: Any) -> Iterator[ValidationError]:
    if validator.is_type(instance, "string") and not matches_pattern(pattern, instance):
        yield ValidationError(f"{instance!r} does not match {pattern!r}")


StrictDraft202012Validator = validators.extend(Draft202012Validator, {"pattern": _pattern})

_DATE_TIME = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:[Zz]|[+-][0-9]{2}:[0-9]{2})"
)


def _is_date_time(instance: Any) -> bool:
    """RFC 3339 date-time that also parses; a trailing newline or a month 13 is not one."""
    if not isinstance(instance, str):
        return True
    if _DATE_TIME.fullmatch(instance) is None:
        raise ValueError(f"{instance!r} is not an RFC 3339 date-time")
    datetime.fromisoformat(instance[:-1] + "+00:00" if instance.endswith(("Z", "z")) else instance)
    return True


def strict_format_checker() -> FormatChecker:
    """A format checker that really checks ``date-time``.

    ``jsonschema`` checks ``date-time`` only when an optional RFC 3339 package is
    installed, so without it any string, including one that later makes
    ``datetime.fromisoformat`` raise, passes the schema.
    """
    checker = FormatChecker()
    checker.checks("date-time", raises=ValueError)(_is_date_time)
    return checker


__all__ = ["StrictDraft202012Validator", "matches_pattern", "strict_format_checker", "strict_pattern_text"]
