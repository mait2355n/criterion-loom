from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from semantic_guard.verification_projection import (
    iter_pointer_records,
    render_verification_projection,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "validation/verification-source.json"
PROJECTION = ROOT / "validation/verification-source.generated.md"
MATRIX = ROOT / "validation/verification-matrix.md"
RENDER_SCRIPT = ROOT / "scripts/render_verification_projection.py"
VALIDATOR = ROOT / "scripts/validate_verification_source.py"


def matrix_evidence_rows(text: str) -> dict[str, tuple[str, str]]:
    section = text.split("## 証拠観測\n", 1)[1].split("\n## ", 1)[0]
    rows: dict[str, tuple[str, str]] = {}
    for line in section.splitlines():
        if not line.startswith("| `evidence."):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        entity_id = cells[0].strip("`")
        if entity_id in rows:
            raise ValueError(f"duplicate evidence row: {entity_id}")
        rows[entity_id] = (cells[1], cells[2])
    return rows


def matrix_source_header(text: str) -> tuple[str, str]:
    projection_time = next(
        line.removeprefix("投影時点: ")
        for line in text.splitlines()
        if line.startswith("投影時点: ")
    )
    source_digest = next(
        line.removeprefix("正本 SHA-256: `").removesuffix("`")
        for line in text.splitlines()
        if line.startswith("正本 SHA-256: `")
    )
    return projection_time, source_digest


class VerificationProjectionTests(unittest.TestCase):
    def test_human_matrix_header_matches_canonical_source(self) -> None:
        source_bytes = SOURCE.read_bytes()
        source = json.loads(source_bytes)
        expected = (
            source["recorded_at"],
            hashlib.sha256(source_bytes).hexdigest(),
        )
        actual = matrix_source_header(MATRIX.read_text(encoding="utf-8"))
        self.assertEqual(actual, expected)

    def test_human_matrix_header_check_detects_stale_source_digest(self) -> None:
        source_digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        text = MATRIX.read_text(encoding="utf-8")
        tampered = text.replace(source_digest, "0" * 64, 1)
        self.assertNotEqual(tampered, text)
        self.assertNotEqual(
            matrix_source_header(tampered)[1],
            source_digest,
        )

    def test_human_matrix_evidence_rows_match_canonical_source(self) -> None:
        source = json.loads(SOURCE.read_text(encoding="utf-8"))
        expected = {
            item["entity_id"]: (
                f'{item["evidence_kind"]} / {item["trust_class"]}',
                f'{item["subject_binding"]["status"]} / {item["freshness"]}',
            )
            for item in source["evidence_observations"]
        }
        actual = matrix_evidence_rows(MATRIX.read_text(encoding="utf-8"))
        self.assertEqual(actual, expected)

    def test_human_matrix_evidence_check_detects_stale_identity(self) -> None:
        source = json.loads(SOURCE.read_text(encoding="utf-8"))
        expected_ids = {
            item["entity_id"] for item in source["evidence_observations"]
        }
        current_id = next(
            entity_id
            for entity_id in expected_ids
            if entity_id.startswith("evidence.origin-requirement.snapshot.")
        )
        text = MATRIX.read_text(encoding="utf-8")
        tampered = text.replace(
            current_id,
            f"{current_id}.stale",
            1,
        )
        self.assertNotEqual(tampered, text)
        self.assertNotEqual(
            set(matrix_evidence_rows(tampered)),
            expected_ids,
        )

    def test_checked_in_projection_is_exact_and_idempotent(self) -> None:
        source_bytes = SOURCE.read_bytes()
        source = json.loads(source_bytes)
        expected = render_verification_projection(
            source,
            source_sha256=hashlib.sha256(source_bytes).hexdigest(),
            source_ref=SOURCE.name,
        )
        self.assertEqual(PROJECTION.read_text(encoding="utf-8"), expected)
        completed = subprocess.run(
            [sys.executable, str(RENDER_SCRIPT), "--check"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertTrue(json.loads(completed.stdout)["matches"])

    def test_pointer_appendix_covers_every_scalar_and_container(self) -> None:
        value = {"a/b": [1, None], "flag": True, "nested": {"~key": "value"}}
        records = list(iter_pointer_records(value))
        by_pointer = {item["pointer"]: item for item in records}
        self.assertEqual(len(records), 7)
        self.assertEqual(by_pointer["/a~1b/0"]["value"], 1)
        self.assertIsNone(by_pointer["/a~1b/1"]["value"])
        self.assertEqual(by_pointer["/nested/~0key"]["value"], "value")
        self.assertEqual(by_pointer["/"]["member_count"], 3)

    def test_validator_rejects_one_value_projection_tamper(self) -> None:
        text = PROJECTION.read_text(encoding="utf-8")
        tampered = text.replace(
            '"human_acceptance"',
            '"human_accepted"',
            1,
        )
        self.assertNotEqual(tampered, text)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".md",
            prefix="verification-projection-tamper-",
            dir=ROOT / "validation",
            delete=False,
        ) as handle:
            handle.write(tampered)
            path = Path(handle.name)
        self.addCleanup(path.unlink, missing_ok=True)
        completed = subprocess.run(
            [sys.executable, str(VALIDATOR), "--projection", str(path)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        result = json.loads(completed.stdout)
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(
            any(error["code"] == "projection_value_mismatch" for error in result["errors"])
        )


if __name__ == "__main__":
    unittest.main()
