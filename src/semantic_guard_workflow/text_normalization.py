"""Input normalization applied once at each audit entry point.

The detectors match literal terms, so two spellings of the same text must reach
them as the same string. Without this, full-width ASCII, decomposed kana
(dakuten as a separate combining mark), zero-width characters, and ``\\r``
line endings silently turn a satisfied rule into a gap or hide a real one.

Normalization removes invisible format characters before NFKC, then unifies
line terminators. It is idempotent. Findings quote the
normalized text, so a quoted excerpt may differ in compatibility forms or
removed formatting (for example ``Ａ`` quoted as ``A``).
"""

from __future__ import annotations

import re
import unicodedata

# BOM / zero-width space, non-joiner, joiner, word joiner, soft hyphen, and the
# bidirectional isolates/marks that editors insert invisibly.
_INVISIBLE = re.compile("[﻿​‌‍⁠­‎‏‪-‮⁦-⁩]")
_LINE_TERMINATORS = re.compile(r"\r\n|\r| | |\x85")


def normalize_audit_text(text: str) -> str:
    """Return ``text`` in the canonical form the detectors expect."""
    if not isinstance(text, str) or not text:
        return text
    # Remove formats first so they cannot keep a base and its combining mark
    # apart until a second normalization pass.
    normalized = unicodedata.normalize("NFKC", _INVISIBLE.sub("", text))
    return _LINE_TERMINATORS.sub("\n", normalized)


def normalization_source_ranges(text: str) -> list[tuple[int, int]]:
    """Map each normalized character to its enclosing original text range.

    Keep combining sequences and compositions (including Hangul and half-width
    voiced marks) together. Expanded compatibility characters intentionally map
    to their whole original character, and removed characters create no entry.
    """
    characters: list[str] = []
    ranges: list[tuple[int, int]] = []
    start = 0
    end = 0
    cluster: list[str] = []

    def flush() -> None:
        normalized = unicodedata.normalize("NFKC", "".join(cluster))
        characters.extend(normalized)
        ranges.extend([(start, end)] * len(normalized))

    for index, character in enumerate(text):
        if _INVISIBLE.fullmatch(character):
            continue
        decomposition = unicodedata.normalize("NFKD", character)
        combining = bool(decomposition and unicodedata.combining(decomposition[0]))
        if cluster and not combining:
            cluster_text = "".join(cluster)
            joins = (
                unicodedata.normalize("NFKC", cluster_text + character)
                != unicodedata.normalize("NFKC", cluster_text) + unicodedata.normalize("NFKC", character)
            )
            if not joins:
                flush()
                cluster = []
        if not cluster:
            start = index
        cluster.append(character)
        end = index + 1
    if cluster:
        flush()

    # The line-terminator pass runs after format removal and NFKC, so even a CR
    # and LF separated by removed source characters now form one output unit.
    result: list[tuple[int, int]] = []
    index = 0
    while index < len(characters):
        if characters[index] == "\r" and index + 1 < len(characters) and characters[index + 1] == "\n":
            right_cluster = ranges[index + 1]
            combined_range = (ranges[index][0], right_cluster[1])
            result.append(combined_range)
            index += 2
            # A combining mark may share LF's original cluster. Keep the new
            # enclosing range for its remaining output characters as well.
            while index < len(characters) and ranges[index] == right_cluster:
                result.append(combined_range)
                index += 1
        else:
            result.append(ranges[index])
            index += 1
    return result
