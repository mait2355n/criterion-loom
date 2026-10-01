from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from semantic_guard_workflow.resources import resource_path


RESOURCE_NAMES = (
    ("schemas", "audit-result.schema.json"),
    ("docs", "conventions", "base-contract.json"),
    ("tests", "fixtures", "requests", "good.md"),
    ("schemas", "request-exploration-review.schema.json"),
)


class ResourcePathTests(unittest.TestCase):
    def assert_layout_resources(self, *, source: bool, present: bool) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            if source:
                package = root / "src" / "semantic_guard_workflow"
                expected_root, decoy_root = package / "_resources", root
            else:
                package = root / "site-packages" / "semantic_guard_workflow"
                expected_root, decoy_root = package / "_resources", root / "site-packages"
            package.mkdir(parents=True)
            # An adjacent pyproject alone must not turn an installed package
            # into a source checkout.
            (root / "pyproject.toml").write_text("[project]\nname = 'semantic-guard'\n")
            for parts in RESOURCE_NAMES:
                with self.subTest(source=source, present=present, resource=parts):
                    expected = expected_root.joinpath(*parts)
                    decoy = decoy_root.joinpath(*parts)
                    decoy.parent.mkdir(parents=True, exist_ok=True)
                    decoy.write_text("unrelated adjacent resource")
                    if present:
                        expected.parent.mkdir(parents=True, exist_ok=True)
                        expected.write_text("owned resource")
                    with patch("semantic_guard_workflow.resources.PACKAGE_ROOT", package):
                        actual = resource_path(*parts)
                    self.assertEqual(actual, expected)
                    if present:
                        self.assertEqual(actual.read_text(), "owned resource")
                    else:
                        self.assertFalse(actual.exists())

    def test_paths_cannot_escape_the_workflow_resource_directory(self) -> None:
        for parts in (("..", "schemas", "audit-result.schema.json"), ("/tmp/elsewhere",)):
            with self.subTest(parts=parts), self.assertRaises(ValueError):
                resource_path(*parts)

    def test_canonical_sibling_cannot_supply_missing_workflow_resources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "semantic_guard_workflow"
            decoy = root / "semantic_guard" / "schemas" / "audit-result.schema.json"
            decoy.parent.mkdir(parents=True)
            decoy.write_text("canonical schema")
            with patch("semantic_guard_workflow.resources.PACKAGE_ROOT", package):
                actual = resource_path("schemas", "audit-result.schema.json")
            self.assertFalse(actual.exists())
            self.assertEqual(actual, package / "_resources" / "schemas" / "audit-result.schema.json")

    def test_source_resources_use_package_owned_directory(self) -> None:
        self.assert_layout_resources(source=True, present=True)

    def test_missing_source_resources_do_not_fall_back_to_adjacent_data(self) -> None:
        self.assert_layout_resources(source=True, present=False)

    def test_installed_resources_ignore_adjacent_source_decoys(self) -> None:
        self.assert_layout_resources(source=False, present=True)

    def test_missing_installed_resources_do_not_fall_back_to_adjacent_data(self) -> None:
        self.assert_layout_resources(source=False, present=False)

    def test_src_named_install_target_is_not_owned_by_another_project(self) -> None:
        self.assert_src_target(project_text="[project]\nname = 'other-project'\n")

    def test_wheel_metadata_takes_precedence_over_matching_source_project(self) -> None:
        self.assert_src_target(
            project_text="[project]\nname = 'semantic-guard'\n", installed=True
        )

    def test_ambiguous_project_metadata_does_not_enable_source_fallback(self) -> None:
        for project_text in ("[", "[project]\n", "project = 'semantic-guard'\n"):
            with self.subTest(project_text=project_text):
                self.assert_src_target(project_text=project_text)

    def assert_src_target(self, *, project_text: str, installed: bool = False) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            target = root / "src"
            package = target / "semantic_guard_workflow"
            package.mkdir(parents=True)
            (root / "pyproject.toml").write_text(project_text)
            if installed:
                metadata = target / "semantic_guard-1.2.0.dev0.dist-info" / "METADATA"
                metadata.parent.mkdir()
                metadata.write_text("Metadata-Version: 2.4\nName: semantic-guard\nVersion: 0.1.0\n")
            for parts in RESOURCE_NAMES:
                with self.subTest(resource=parts):
                    expected = (package / "_resources").joinpath(*parts)
                    decoy = root.joinpath(*parts)
                    expected.parent.mkdir(parents=True, exist_ok=True)
                    expected.write_text("installed resource")
                    decoy.parent.mkdir(parents=True, exist_ok=True)
                    decoy.write_text("unrelated project resource")
                    with patch("semantic_guard_workflow.resources.PACKAGE_ROOT", package):
                        self.assertEqual(resource_path(*parts), expected)


if __name__ == "__main__":
    unittest.main()
