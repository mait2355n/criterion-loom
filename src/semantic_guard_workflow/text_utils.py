from __future__ import annotations

import re
from collections.abc import Iterable

DEFAULT_SNIPPET_LIMIT = 220


def combine(*parts: str) -> str:
    return "\n".join(part for part in parts if part)


def has_any(text: str, needles: Iterable[str]) -> bool:
    lower = text.lower()
    return any(needle.lower() in lower for needle in needles)


def first_match(text: str, needles: Iterable[str]) -> str:
    lower = text.lower()
    for needle in needles:
        index = lower.find(needle.lower())
        if index >= 0:
            return excerpt_around(text, index, index + len(needle))
    return ""


def excerpt_around(text: str, start: int, end: int, limit: int = DEFAULT_SNIPPET_LIMIT) -> str:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end < 0:
        line_end = len(text)
    line = text[line_start:line_end].strip()
    if line:
        relative_start = max(0, start - line_start)
        relative_end = max(relative_start, end - line_start)
        if len(line) > limit and relative_start >= limit // 2:
            return compact_snippet_around(line, relative_start, relative_end, limit)
        return compact_snippet(line, limit)

    before = max(text.rfind(mark, 0, start) for mark in ("\n", "。", ".", "!", "?"))
    after_candidates = [text.find(mark, end) for mark in ("\n", "。", ".", "!", "?")]
    after_candidates = [candidate for candidate in after_candidates if candidate >= 0]
    snippet_start = before + 1 if before >= 0 else 0
    snippet_end = min(after_candidates) + 1 if after_candidates else len(text)
    return compact_snippet(text[snippet_start:snippet_end].strip(), limit)


def compact_snippet(text: str, limit: int = DEFAULT_SNIPPET_LIMIT) -> str:
    cleaned = "\n".join(line.rstrip() for line in text.strip().splitlines())
    if len(cleaned) <= limit:
        return cleaned

    boundary_chars = ".!?。！？、，,;；:：)]}」』"
    cut = -1
    for index in range(limit - 1, max(0, limit // 2), -1):
        if cleaned[index] in boundary_chars or cleaned[index].isspace():
            cut = index + 1
            break
    if cut < 0:
        cut = limit

    return cleaned[:cut].rstrip() + "..."


def compact_snippet_around(text: str, start: int, end: int, limit: int = DEFAULT_SNIPPET_LIMIT) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned

    content_limit = max(32, limit - 6)
    window_start = max(0, start - content_limit // 2)
    window_end = min(len(cleaned), window_start + content_limit)
    if end > window_end:
        window_end = min(len(cleaned), end + content_limit // 2)
        window_start = max(0, window_end - content_limit)

    if window_start > 0:
        whitespace = cleaned.find(" ", window_start, min(len(cleaned), window_start + 24))
        punctuation = min(
            [idx for idx in (cleaned.find(mark, window_start, min(len(cleaned), window_start + 24)) for mark in "、，,;；:：") if idx >= 0],
            default=-1,
        )
        boundary = whitespace if whitespace >= 0 else punctuation
        if boundary >= 0 and boundary < start:
            window_start = boundary + 1

    if window_end < len(cleaned):
        for idx in range(window_end, max(window_start, window_end - 40), -1):
            if cleaned[idx - 1].isspace() or cleaned[idx - 1] in ".!?。！？、，,;；:：)]}」』":
                window_end = idx
                break

    prefix = "..." if window_start > 0 else ""
    suffix = "..." if window_end < len(cleaned) else ""
    return prefix + cleaned[window_start:window_end].strip() + suffix


def compact_code_snippet(text: str, limit: int = DEFAULT_SNIPPET_LIMIT) -> str:
    cleaned = "\n".join(line.rstrip() for line in text.strip().splitlines())
    if len(cleaned) <= limit:
        return cleaned

    lines = cleaned.splitlines()
    selected: list[str] = []
    total = 0
    for line in lines:
        next_total = total + len(line) + (1 if selected else 0)
        if selected and next_total > max(16, limit - 8):
            break
        selected.append(line)
        total = next_total
        if total >= max(16, limit - 8):
            break

    if not selected:
        return compact_snippet(cleaned, limit)

    if selected[0].startswith("```") and not selected[-1].startswith("```"):
        selected.append("...")
        selected.append("```")
    else:
        selected[-1] = selected[-1].rstrip() + "..."
    return "\n".join(selected)


def strip_code_blocks(text: str) -> str:
    return re.sub(r"```.*?```", " ", text, flags=re.DOTALL)


def unique_nonempty(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = item.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result
