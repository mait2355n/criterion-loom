from __future__ import annotations

import ast
import importlib
from importlib.util import resolve_name
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "src" / "semantic_guard_workflow"

MODULE_EXPORTS = {
    "codex_exec_runtime": (
        "runtime.codex_exec",
        [
            "DEFAULT_CODEX_MODEL",
            "DEFAULT_TIMEOUT_SECONDS",
            "CodexExecRuntimeResult",
            "Runner",
            "Validator",
            "build_codex_exec_runtime_command",
            "command_display",
            "parse_json_object",
            "run_codex_exec_runtime",
        ],
    ),
    "job_runtime": (
        "runtime.jobs",
        [
            "BackgroundJobStore",
            "JobRuntimeConfig",
            "Runner",
            "utc_now",
        ],
    ),
    "codex_exec_review": (
        "runtime.review",
        [
            "DEFAULT_CODEX_MODEL",
            "DEFAULT_TIMEOUT_SECONDS",
            "CodexExecReviewRequest",
            "CodexExecReviewResult",
            "Runner",
            "build_codex_exec_command",
            "command_display",
            "run_codex_exec_review",
        ],
    ),
    "codex_exec_exploration": (
        "runtime.exploration",
        [
            "DEFAULT_CODEX_MODEL",
            "DEFAULT_TIMEOUT_SECONDS",
            "CodexExecExplorationRequest",
            "CodexExecExplorationResult",
            "Runner",
            "build_codex_exec_exploration_command",
            "command_display",
            "run_codex_exec_exploration",
        ],
    ),
    "review_jobs": (
        "runtime.review_jobs",
        [
            "DEFAULT_CODEX_MODEL",
            "DEFAULT_TIMEOUT_SECONDS",
            "CodexExecReviewRequest",
            "CodexExecReviewResult",
            "ReviewJob",
            "ReviewJobStore",
            "Runner",
            "build_codex_exec_command",
            "run_codex_exec_review",
            "start_review_if_needed_job",
        ],
    ),
    "exploration_jobs": (
        "runtime.exploration_jobs",
        [
            "CodexExecExplorationRequest",
            "CodexExecExplorationResult",
            "ExplorationJob",
            "ExplorationJobStore",
            "Runner",
            "build_codex_exec_exploration_command",
            "run_codex_exec_exploration",
        ],
    ),
}


class RuntimePackageLayoutTests(unittest.TestCase):
    def test_legacy_modules_explicitly_reexport_canonical_objects(self) -> None:
        for legacy_name, (canonical_name, expected_exports) in MODULE_EXPORTS.items():
            with self.subTest(legacy_name=legacy_name):
                legacy = importlib.import_module(f"semantic_guard_workflow.{legacy_name}")
                canonical = importlib.import_module(f"semantic_guard_workflow.{canonical_name}")

                self.assertEqual(legacy.__all__, expected_exports)
                for export_name in expected_exports:
                    self.assertIs(getattr(legacy, export_name), getattr(canonical, export_name))

    def test_implementations_live_under_runtime_package(self) -> None:
        for legacy_name, (canonical_name, _expected_exports) in MODULE_EXPORTS.items():
            with self.subTest(legacy_name=legacy_name):
                legacy = importlib.import_module(f"semantic_guard_workflow.{legacy_name}")
                canonical = importlib.import_module(f"semantic_guard_workflow.{canonical_name}")

                self.assertEqual(Path(legacy.__file__).parent, PACKAGE_ROOT)
                self.assertEqual(Path(canonical.__file__).parent, PACKAGE_ROOT / "runtime")

    def test_legacy_modules_are_one_layer_shims(self) -> None:
        for legacy_name, (canonical_name, _expected_exports) in MODULE_EXPORTS.items():
            with self.subTest(legacy_name=legacy_name):
                tree = ast.parse((PACKAGE_ROOT / f"{legacy_name}.py").read_text(encoding="utf-8"))
                definitions = [
                    node
                    for node in tree.body
                    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                imported_modules = {
                    node.module
                    for node in tree.body
                    if isinstance(node, ast.ImportFrom) and node.module is not None
                }

                self.assertEqual(definitions, [])
                self.assertEqual(imported_modules, {f"semantic_guard_workflow.{canonical_name}"})

    def test_internal_source_does_not_import_legacy_runtime_shims(self) -> None:
        legacy_modules = {f"semantic_guard_workflow.{name}" for name in MODULE_EXPORTS}
        violations: list[str] = []

        for path in PACKAGE_ROOT.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            relative = path.relative_to(PACKAGE_ROOT).with_suffix("")
            module_parts = relative.parts[:-1] if relative.name == "__init__" else relative.parts
            package_parts = (
                module_parts
                if relative.name == "__init__"
                else module_parts[:-1]
            )
            package = ".".join(("semantic_guard_workflow", *package_parts))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    imported = (
                        resolve_name(
                            "." * node.level + (node.module or ""),
                            package,
                        )
                        if node.level
                        else node.module or ""
                    )
                    candidates = [imported]
                    candidates.extend(
                        f"{imported}.{alias.name}"
                        for alias in node.names
                        if alias.name != "*"
                    )
                    violations.extend(
                        f"{path.relative_to(PACKAGE_ROOT)}:{node.lineno}:{candidate}"
                        for candidate in candidates
                        if candidate in legacy_modules
                    )
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in legacy_modules:
                            violations.append(f"{path.relative_to(PACKAGE_ROOT)}:{node.lineno}:{alias.name}")

        self.assertEqual(violations, [])

    def test_runtime_package_init_has_no_eager_imports(self) -> None:
        tree = ast.parse((PACKAGE_ROOT / "runtime" / "__init__.py").read_text(encoding="utf-8"))
        eager_imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]

        self.assertEqual(eager_imports, [])


if __name__ == "__main__":
    unittest.main()
