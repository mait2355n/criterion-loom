"""Input normalization applied once at each audit entry point.

The detectors match literal terms, so two spellings of the same text must reach
them as the same string. Without this, full-width ASCII, decomposed kana
(dakuten as a separate combining mark), zero-width characters, and ``\\r``
line endings silently turn a satisfied rule into a gap or hide a real one.

Normalization removes invisible format characters (every Unicode ``Cf``
character, variation selectors, U+034F, U+180B-180F, and tag characters) before
NFKC, then unifies line terminators. It is idempotent. Findings quote the
normalized text, so a quoted excerpt may differ in compatibility forms or
removed formatting (for example ``Ａ`` quoted as ``A``).
"""

from __future__ import annotations

import re
import unicodedata
from functools import cache

# Code points that render as nothing yet split a word for a literal matcher, in
# addition to every Unicode "Cf" (format) character: the combining grapheme
# joiner, Mongolian free variation selectors, the variation selectors, and the
# tag characters used for emoji flags (and for hidden text).
_EXTRA_INVISIBLE = (
    (0x034F, 0x034F),
    (0x180B, 0x180F),
    (0xFE00, 0xFE0F),
    (0xE0000, 0xE007F),
    (0xE0100, 0xE01EF),
)
# "Cf" occurs only in the BMP, plane 1, and the tag block; scanning these ranges
# keeps the one-time build under a tenth of a second.
_SCANNED = ((0x0000, 0x1FFFF), (0xE0000, 0xE01FF))
_LINE_TERMINATORS = re.compile(r"\r\n|\r|\u2028|\u2029|\x85")


@cache
def _invisible_pattern() -> re.Pattern[str]:
    """One character class over the Unicode ``Cf`` category plus the extras.

    Built from ``unicodedata`` so it follows the interpreter's Unicode version;
    it is the only definition of "invisible" in the package.
    """
    points = {
        code
        for low, high in _SCANNED
        for code in range(low, high + 1)
        if unicodedata.category(chr(code)) == "Cf"
    }
    for low, high in _EXTRA_INVISIBLE:
        points.update(range(low, high + 1))
    ordered = sorted(points)
    spans: list[tuple[int, int]] = []
    for code in ordered:
        if spans and code == spans[-1][1] + 1:
            spans[-1] = (spans[-1][0], code)
        else:
            spans.append((code, code))
    body = "".join(
        re.escape(chr(low)) if low == high else f"{re.escape(chr(low))}-{re.escape(chr(high))}"
        for low, high in spans
    )
    return re.compile(f"[{body}]")


def is_invisible_character(character: str) -> bool:
    """Whether ``character`` is removed by :func:`normalize_audit_text`."""
    return _invisible_pattern().fullmatch(character) is not None


def normalize_audit_text(text: str) -> str:
    """Return ``text`` in the canonical form the detectors expect."""
    if not isinstance(text, str) or not text:
        return text
    # Remove formats first so they cannot keep a base and its combining mark
    # apart until a second normalization pass.
    normalized = unicodedata.normalize("NFKC", _invisible_pattern().sub("", text))
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
        if is_invisible_character(character):
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
