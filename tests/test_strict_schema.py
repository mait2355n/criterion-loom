from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

from semantic_guard.strict_schema import (
    StrictDraft202012Validator,
    matches_pattern,
    strict_format_checker,
    strict_pattern_text,
)

ROOT = Path(__file__).resolve().parents[1]
NAMESPACES = ("semantic_guard", "semantic_guard_workflow", "semantic_guard_vnext", "semantic_guard_u10_broker")


def _patterns(node: object):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "pattern" and isinstance(value, str):
                yield value
            else:
                yield from _patterns(value)
    elif isinstance(node, list):
        for item in node:
            yield from _patterns(item)


class StrictPatternTests(unittest.TestCase):
    def test_a_trailing_newline_does_not_satisfy_an_end_anchored_pattern(self) -> None:
        validator = StrictDraft202012Validator({"type": "string", "pattern": r"^sha256:[0-9a-f]{4}$"})

        self.assertTrue(validator.is_valid("sha256:abcd"))
        self.assertFalse(validator.is_valid("sha256:abcd\n"))
        self.assertFalse(validator.is_valid("x sha256:abcd"))

    def test_only_the_end_anchor_changes(self) -> None:
        self.assertEqual(strict_pattern_text(r"^a$"), r"^a\Z")
        self.assertEqual(strict_pattern_text(r"^[a$]+$"), r"^[a$]+\Z")
        self.assertEqual(strict_pattern_text(r"^a\$$"), r"^a\$\Z")
        self.assertEqual(strict_pattern_text(r"^(?:a|b)$"), r"^(?:a|b)\Z")
        self.assertEqual(strict_pattern_text(r"^[^]$]$"), r"^[^]$]\Z")
        self.assertTrue(matches_pattern(r"a", "xay\n"))  # an unanchored pattern may match anywhere

    def test_every_published_pattern_still_compiles_and_loses_its_loose_anchor(self) -> None:
        checked = 0
        for path in sorted((ROOT / "schemas").rglob("*.json")):
            for pattern in _patterns(json.loads(path.read_text(encoding="utf-8"))):
                strict = strict_pattern_text(pattern)
                with self.subTest(schema=path.name, pattern=pattern):
                    re.compile(strict)
                    self.assertNotRegex(strict, r"(?<!\\)(?:\\\\)*\$(?![^\[]*\])")
                checked += 1
        self.assertGreater(checked, 50)

    def test_date_time_is_really_checked(self) -> None:
        validator = StrictDraft202012Validator(
            {"type": "string", "format": "date-time"}, format_checker=strict_format_checker()
        )

        for good in ("2026-08-28T00:00:00Z", "2026-08-28t00:00:00z", "2026-08-28T09:00:00.250+09:00"):
            with self.subTest(value=good):
                self.assertTrue(validator.is_valid(good))
        for bad in ("2026-08-28T00:00:00Z\n", "2026-13-45T00:00:00Z", "yesterday", "2026-08-28 00:00:00Z", ""):
            with self.subTest(value=bad):
                self.assertFalse(validator.is_valid(bad))


class ValidatorConstructionTests(unittest.TestCase):
    def test_no_module_builds_a_loose_validator(self) -> None:
        offenders = []
        for namespace in NAMESPACES:
            for path in sorted((ROOT / "src" / namespace).rglob("*.py")):
                for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                    if re.search(r"(?<![A-Za-z_])Draft202012Validator\(", line):
                        offenders.append(f"{path.relative_to(ROOT)}:{number}")

        self.assertEqual(offenders, [])

    def test_the_copies_in_each_namespace_are_identical(self) -> None:
        texts = {namespace: (ROOT / "src" / namespace / "strict_schema.py").read_text(encoding="utf-8") for namespace in NAMESPACES}

        self.assertEqual(len(set(texts.values())), 1, "strict_schema.py must be byte-identical in every namespace")


if __name__ == "__main__":
    unittest.main()
