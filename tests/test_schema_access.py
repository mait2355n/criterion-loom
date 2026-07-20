from __future__ import annotations

import unittest

from semantic_guard.schema_access import schema_directory, schema_path


class SchemaAccessTests(unittest.TestCase):
    def test_resolves_source_or_packaged_schema_directory(self) -> None:
        directory = schema_directory()

        self.assertTrue((directory / "common.schema.json").is_file())
        self.assertEqual(schema_path("state-assessment.schema.json").parent, directory)

    def test_rejects_path_selection(self) -> None:
        for value in ("../common.schema.json", "/tmp/common.schema.json", "common.json"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    schema_path(value)


if __name__ == "__main__":
    unittest.main()
