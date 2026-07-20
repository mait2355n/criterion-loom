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
RENDER_SCRIPT = ROOT / "scripts/render_verification_projection.py"
VALIDATOR = ROOT / "scripts/validate_verification_source.py"


class VerificationProjectionTests(unittest.TestCase):
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
