from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from semantic_guard.legacy_runner import (
    REQUIRED_LEGACY_BASELINE_PATHS,
    _validate_legacy_result,
    check_baseline,
    normalize_legacy_result,
    run_legacy_request,
)


SCHEMA_VERSION = "semantic-guard-legacy-baseline/v1"
PIN_PROFILE = "semantic-guard-requirement-relations-legacy/v1"


def manifest_payload(entries: list[dict[str, str]]) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "pin_profile": PIN_PROFILE,
        "runtime": {
            "interpreter_path": ".venv/bin/python",
            "sha256": hashlib.sha256(b"fixture runtime").hexdigest(),
            "python_version": "Python fixture",
        },
        "coverage": {
            "scopes": [{"root": "src/semantic_guard", "suffixes": [".py"]}],
            "exact_paths": sorted(REQUIRED_LEGACY_BASELINE_PATHS),
        },
        "source_digests": entries,
    }


def write_pinned_sources(root: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for relative in sorted(REQUIRED_LEGACY_BASELINE_PATHS):
        source = root / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(f"fixture:{relative}", encoding="utf-8")
        entries.append(
            {
                "path": relative,
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            }
        )
    interpreter = root / ".venv" / "bin" / "python"
    interpreter.parent.mkdir(parents=True, exist_ok=True)
    interpreter.write_bytes(b"fixture runtime")
    return entries


class LegacyRunnerTests(unittest.TestCase):
    def test_baseline_drift_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entries = write_pinned_sources(root)
            entries[0]["sha256"] = "0" * 64
            manifest = root / "baseline.json"
            manifest.write_text(
                json.dumps(manifest_payload(entries)),
                encoding="utf-8",
            )

            result = check_baseline(root, manifest)

            self.assertEqual(result.status, "drifted")
            self.assertEqual(result.checked_files, len(REQUIRED_LEGACY_BASELINE_PATHS) + 1)
            self.assertEqual(result.mismatches[0]["reason"], "sha256_mismatch")

    def test_empty_or_malformed_baseline_is_invalid_not_matched(self) -> None:
        invalid_manifests = (
            {},
            {
                "schema_version": SCHEMA_VERSION,
                "pin_profile": PIN_PROFILE,
                "runtime": manifest_payload([])["runtime"],
                "coverage": {
                    "scopes": [{"root": "src/semantic_guard", "suffixes": [".py"]}],
                    "exact_paths": sorted(REQUIRED_LEGACY_BASELINE_PATHS),
                },
                "source_digests": [],
            },
            {
                "schema_version": SCHEMA_VERSION,
                "pin_profile": PIN_PROFILE,
                "runtime": manifest_payload([])["runtime"],
                "coverage": {
                    "scopes": [{"root": "src/semantic_guard", "suffixes": [".py"]}],
                    "exact_paths": sorted(REQUIRED_LEGACY_BASELINE_PATHS),
                },
                "source_digests": "not-an-array",
            },
            {
                "schema_version": SCHEMA_VERSION,
                "pin_profile": PIN_PROFILE,
                "runtime": manifest_payload([])["runtime"],
                "coverage": {
                    "scopes": [{"root": "src/semantic_guard", "suffixes": [".py"]}],
                    "exact_paths": sorted(REQUIRED_LEGACY_BASELINE_PATHS),
                },
                "source_digests": [{"path": "../escape", "sha256": "0" * 64}],
            },
            {
                "schema_version": SCHEMA_VERSION,
                "pin_profile": PIN_PROFILE,
                "runtime": manifest_payload([])["runtime"],
                "coverage": {
                    "scopes": [{"root": "src/semantic_guard", "suffixes": [".py"]}],
                    "exact_paths": sorted(REQUIRED_LEGACY_BASELINE_PATHS),
                },
                "source_digests": [{"path": "a.txt", "sha256": "not-a-digest"}],
            },
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, payload in enumerate(invalid_manifests):
                manifest = root / f"invalid-{index}.json"
                manifest.write_text(json.dumps(payload), encoding="utf-8")

                result = check_baseline(root, manifest)

                self.assertEqual(result.status, "invalid_manifest", payload)
                self.assertEqual(result.checked_files, 0)

    def test_empty_manifest_file_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "baseline.json"
            manifest.write_text("", encoding="utf-8")

            result = check_baseline(root, manifest)

            self.assertEqual(result.status, "invalid_manifest")
            self.assertEqual(result.checked_files, 0)

    def test_invalid_baseline_cannot_be_overridden_as_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "baseline.json"
            manifest.write_text("{}", encoding="utf-8")

            result = run_legacy_request(
                text="Purpose: test",
                legacy_root=root,
                baseline_manifest=manifest,
                adapter_script=root / "adapter.py",
                allow_baseline_drift=True,
            )

            self.assertEqual(result.execution.status, "baseline_invalid")
            self.assertEqual(result.execution.baseline.status, "invalid_manifest")
            self.assertIsNone(result.execution.exit_code)

    def test_valid_nonempty_baseline_can_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entries = write_pinned_sources(root)
            manifest = root / "baseline.json"
            manifest.write_text(
                json.dumps(manifest_payload(entries)),
                encoding="utf-8",
            )

            result = check_baseline(root, manifest)

            self.assertEqual(result.status, "matched")
            self.assertEqual(result.checked_files, len(REQUIRED_LEGACY_BASELINE_PATHS) + 1)

    def test_new_file_in_covered_scope_causes_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entries = write_pinned_sources(root)
            manifest = root / "baseline.json"
            manifest.write_text(
                json.dumps(manifest_payload(entries)),
                encoding="utf-8",
            )
            added = root / "src" / "semantic_guard" / "untracked.py"
            added.write_text("new behavior", encoding="utf-8")

            result = check_baseline(root, manifest)

            self.assertEqual(result.status, "drifted")
            self.assertIn(
                {"path": "src/semantic_guard/untracked.py", "reason": "untracked_in_covered_scope"},
                result.mismatches,
            )

    def test_arbitrary_json_object_is_not_a_valid_legacy_audit_result(self) -> None:
        root = Path(__file__).resolve().parents[1]

        valid, reason = _validate_legacy_result(root, {})

        self.assertFalse(valid)
        self.assertIn("schema violation", reason)

    def test_adapter_must_be_manifest_pinned_even_when_drift_override_is_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entries = write_pinned_sources(root)
            manifest = root / "baseline.json"
            manifest.write_text(
                json.dumps(manifest_payload(entries)),
                encoding="utf-8",
            )
            unpinned = root / "untrusted-adapter.py"
            unpinned.write_text("print('{}')", encoding="utf-8")

            result = run_legacy_request(
                text="Purpose: test",
                legacy_root=root,
                baseline_manifest=manifest,
                adapter_script=unpinned,
                allow_baseline_drift=True,
            )

            self.assertEqual(result.execution.status, "adapter_unpinned")
            self.assertEqual(result.execution.adapter_pin_status, "untrusted")

    def test_suppressed_alias_is_not_double_counted(self) -> None:
        item = {
            "rule_id": "req.relation.verification_target_mismatch",
            "emission_status": "unknown",
            "reason": "not asserted",
        }
        normalized = normalize_legacy_result(
            {
                "phase": "audit_request",
                "status": "pass",
                "score": 1.0,
                "findings": [],
                "missing": [],
                "next_actions": [],
                "details": {
                    "non_emitted_rules": [item],
                    "suppressed_rules": [item],
                    "requirement_relation_summary": {},
                },
            }
        )

        self.assertEqual(normalized["non_emitted_rules"], [item])


if __name__ == "__main__":
    unittest.main()
