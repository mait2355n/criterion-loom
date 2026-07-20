from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path
from typing import Any


CORPUS_PATH = Path(__file__).parent / "field-corpus" / "corpus-2026-06-04.json"

ALLOWED_BUCKETS = {"good_warning", "noisy_warning", "miss"}
ALLOWED_PHASES = {"understand_target", "audit_request", "audit_plan", "audit_diff", "finish_check"}
ALLOWED_ACTIONS = {"keep", "suppress_or_weaken", "add_detector", "manual_review"}
ALLOWED_STATUSES = {"candidate", "accepted", "deferred"}
REQUIRED_FIELDS = {
    "id",
    "bucket",
    "phase",
    "source",
    "summary",
    "input",
    "expected_review",
    "current_behavior",
    "target_rule_ids",
    "action",
    "status",
}


class FieldCorpusTests(unittest.TestCase):
    def test_corpus_shape_and_balance(self) -> None:
        corpus = _load_corpus()

        self.assertGreaterEqual(len(corpus), 30)
        counts = Counter()
        seen_ids: set[str] = set()

        for entry in corpus:
            self.assertIsInstance(entry, dict)
            self.assertTrue(REQUIRED_FIELDS <= entry.keys())

            entry_id = _required_string(entry, "id")
            self.assertNotIn(entry_id, seen_ids)
            seen_ids.add(entry_id)

            bucket = _required_string(entry, "bucket")
            phase = _required_string(entry, "phase")
            action = _required_string(entry, "action")
            status = _required_string(entry, "status")
            counts[bucket] += 1

            self.assertIn(bucket, ALLOWED_BUCKETS)
            self.assertIn(phase, ALLOWED_PHASES)
            self.assertIn(action, ALLOWED_ACTIONS)
            self.assertIn(status, ALLOWED_STATUSES)

            for key in ("source", "summary", "input", "expected_review", "current_behavior"):
                self.assertTrue(_required_string(entry, key), f"{entry_id}: {key} must be non-empty")

            rule_ids = entry["target_rule_ids"]
            self.assertIsInstance(rule_ids, list, f"{entry_id}: target_rule_ids must be a list")
            self.assertGreater(len(rule_ids), 0, f"{entry_id}: target_rule_ids must not be empty")
            for rule_id in rule_ids:
                self.assertIsInstance(rule_id, str, f"{entry_id}: rule id must be a string")
                self.assertTrue(rule_id, f"{entry_id}: rule id must be non-empty")

        for bucket in ALLOWED_BUCKETS:
            self.assertGreaterEqual(counts[bucket], 10, f"corpus needs at least 10 {bucket} entries")


def _load_corpus() -> list[dict[str, Any]]:
    data = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise AssertionError("field corpus must be a JSON array")
    return data


def _required_string(entry: dict[str, Any], key: str) -> str:
    value = entry[key]
    if not isinstance(value, str):
        raise AssertionError(f"{entry.get('id', '<unknown>')}: {key} must be a string")
    return value.strip()


if __name__ == "__main__":
    unittest.main()
