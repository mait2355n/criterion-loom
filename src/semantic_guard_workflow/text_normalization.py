"""Input normalization applied once at each audit entry point.

The detectors match literal terms, so two spellings of the same text must reach
them as the same string. Without this, full-width ASCII, decomposed kana
(dakuten as a separate combining mark), zero-width characters, and ``\\r``
line endings silently turn a satisfied rule into a gap or hide a real one.

Normalization is NFKC plus removal of invisible format characters and
unification of line terminators. It is idempotent. Findings quote the
normalized text, so a quoted excerpt may differ from the caller's bytes in
compatibility forms only (for example ``Ａ`` quoted as ``A``).
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
    normalized = unicodedata.normalize("NFKC", text)
    normalized = _INVISIBLE.sub("", normalized)
    return _LINE_TERMINATORS.sub("\n", normalized)
