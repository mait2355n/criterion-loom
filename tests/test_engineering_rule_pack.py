from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "validation/engineering-rule-pack.candidate.json"
SCRIPT = ROOT / "scripts/validate_engineering_rule_pack.py"


class EngineeringRulePackValidatorTests(unittest.TestCase):
    def _source(self) -> dict:
        return json.loads(PACK.read_text(encoding="utf-8"))

    def _write_pack(self, value: dict) -> Path:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".json",
            prefix="engineering-rule-pack-test-",
            dir=ROOT / "validation",
            delete=False,
        ) as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            path = Path(handle.name)
        self.addCleanup(path.unlink, missing_ok=True)
        return path

    def _run(self, pack: Path | None = None) -> tuple[subprocess.CompletedProcess[str], dict]:
        arguments = [sys.executable, str(SCRIPT)]
        if pack is not None:
            arguments.extend(["--pack", str(pack)])
        completed = subprocess.run(
            arguments,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=20.0,
            check=False,
        )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:  # pragma: no cover - assertion aid.
            self.fail(
                f"validator did not emit JSON: returncode={completed.returncode}, "
                f"stdout={completed.stdout!r}, stderr={completed.stderr!r}, error={exc}"
            )
        return completed, payload

    @staticmethod
    def _codes(payload: dict) -> set[str]:
        return {item["code"] for item in payload["errors"]}

    def test_candidate_register_passes_with_exact_local_coverage(self) -> None:
        completed, payload = self._run()
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(set(payload["checks"].values()), {"passed"})
        self.assertEqual(payload["counts"]["profile_obligations"], 11)
        self.assertEqual(payload["counts"]["local_direct_rules"], 11)
        self.assertEqual(payload["counts"]["rules"], 11)

    def test_removed_mapping_fails_obligation_and_direct_rule_coverage(self) -> None:
        value = self._source()
        value["rules"].pop()
        completed, payload = self._run(self._write_pack(value))
        self.assertEqual(completed.returncode, 1)
        self.assertIn("missing_obligation_mapping", self._codes(payload))
        self.assertIn("missing_direct_rule_mapping", self._codes(payload))

    def test_false_adopted_rule_fails_closed_without_review_and_adoption(self) -> None:
        value = self._source()
        value["rules"][0]["adoption_state"] = "adopted"
        value["rules"][0]["runtime_authority"] = "audit_decision"
        completed, payload = self._run(self._write_pack(value))
        codes = self._codes(payload)
        self.assertEqual(completed.returncode, 1)
        self.assertIn("adoption_evidence_missing", codes)
        self.assertIn("independent_review_evidence_missing", codes)
        self.assertIn("human_adoption_not_completed", codes)
        self.assertIn("adopted_rule_uses_unbound_source", codes)
        self.assertIn("rule_adopted_inside_unadopted_pack", codes)

    def test_missing_source_section_locator_fails_schema(self) -> None:
        value = self._source()
        del value["rules"][0]["source_refs"][0]["section_locator"]
        completed, payload = self._run(self._write_pack(value))
        self.assertEqual(completed.returncode, 1)
        self.assertIn("schema_validation_failed", self._codes(payload))

    def test_missing_countercondition_fails_schema(self) -> None:
        value = self._source()
        value["rules"][0]["counterconditions"] = []
        completed, payload = self._run(self._write_pack(value))
        self.assertEqual(completed.returncode, 1)
        self.assertIn("schema_validation_failed", self._codes(payload))

    def test_dangling_source_reference_fails(self) -> None:
        value = self._source()
        value["rules"][0]["source_refs"][0]["source_id"] = "source.does-not-exist"
        completed, payload = self._run(self._write_pack(value))
        self.assertEqual(completed.returncode, 1)
        self.assertIn("dangling_source_ref", self._codes(payload))

    def test_dangling_obligation_reference_fails(self) -> None:
        value = self._source()
        value["rules"][0]["profile_obligation_refs"] = ["func.does_not_exist"]
        completed, payload = self._run(self._write_pack(value))
        codes = self._codes(payload)
        self.assertEqual(completed.returncode, 1)
        self.assertIn("dangling_obligation_ref", codes)
        self.assertIn("missing_obligation_mapping", codes)

    def test_dangling_local_rule_reference_fails(self) -> None:
        value = self._source()
        value["rules"][0]["local_implementation_rule_refs"][0]["rule_id"] = (
            "direct.structured.does-not-exist/v99"
        )
        completed, payload = self._run(self._write_pack(value))
        codes = self._codes(payload)
        self.assertEqual(completed.returncode, 1)
        self.assertIn("dangling_direct_rule_ref", codes)
        self.assertIn("missing_direct_rule_mapping", codes)

    def test_iso_revision_without_replacement_trigger_fails(self) -> None:
        value = self._source()
        iso = next(
            source
            for source in value["sources"]
            if source["source_id"] == "source.iso-iec-ieee-29148.2018"
        )
        iso["review_triggers"] = ["Review metadata periodically."]
        completed, payload = self._run(self._write_pack(value))
        self.assertEqual(completed.returncode, 1)
        self.assertIn("revision_review_trigger_missing", self._codes(payload))

    def test_exact_source_without_verified_digest_fails(self) -> None:
        value = self._source()
        acquisition = value["sources"][0]["acquisition"]
        acquisition["state"] = "exact_text_acquired"
        acquisition["exact_source_text_acquired"] = True
        acquisition["content_digest"] = {"state": "missing", "algorithm": "sha256"}
        completed, payload = self._run(self._write_pack(value))
        self.assertEqual(completed.returncode, 1)
        self.assertIn("source_digest_missing", self._codes(payload))

    def test_duplicate_rule_identity_and_mappings_fail(self) -> None:
        value = self._source()
        value["rules"].append(deepcopy(value["rules"][0]))
        completed, payload = self._run(self._write_pack(value))
        codes = self._codes(payload)
        self.assertEqual(completed.returncode, 1)
        self.assertIn("duplicate_rule_version", codes)
        self.assertIn("duplicate_obligation_mapping", codes)
        self.assertIn("duplicate_direct_rule_mapping", codes)

    def test_candidate_rule_cannot_receive_runtime_authority(self) -> None:
        value = self._source()
        value["rules"][0]["runtime_authority"] = "advisory"
        completed, payload = self._run(self._write_pack(value))
        self.assertEqual(completed.returncode, 1)
        self.assertIn("runtime_authority_for_unadopted_rule", self._codes(payload))


if __name__ == "__main__":
    unittest.main()
