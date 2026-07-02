from __future__ import annotations

import re
from typing import Iterable


def has_any(text: str, terms: Iterable[str]) -> bool:
    lowered = text.lower()
    for term in terms:
        normalized = term.lower()
        if _is_ascii_word(normalized):
            if re.search(rf"(?<![a-z0-9_]){re.escape(normalized)}(?![a-z0-9_])", lowered):
                return True
        elif normalized in lowered:
            return True
    return False


def matched_terms(text: str, terms: Iterable[str]) -> list[str]:
    return [term for term in terms if has_any(text, [term])]


def unique_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def _is_ascii_word(term: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9_ -]+", term))
