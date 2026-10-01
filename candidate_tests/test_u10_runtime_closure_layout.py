from __future__ import annotations

import ast
from pathlib import Path
import unittest

import semantic_guard_u10_broker.core as core
import semantic_guard_u10_broker.runtime_closure as runtime_closure


PACKAGE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "semantic_guard_u10_broker"
)
CORE_MODULE = "semantic_guard_u10_broker.core"
RUNTIME_CLOSURE_MODULE = "semantic_guard_u10_broker.runtime_closure"
PROTECTED_IO_MODULE = "semantic_guard_u10_broker.protected_io"
DARWIN_ACL_MODULE = "semantic_guard_u10_broker.darwin_acl"
MOVED_CONSTANTS = {
    "_RUNTIME_CLOSURE_PROFILE",
    "_RUNTIME_OS_EXCLUSION_PROFILE",
    "_RUNTIME_OS_ASSET_ROOTS",
    "_RUNTIME_PROBE_ENVIRONMENT",
    "_RUNTIME_PROBE",
}
MOVED_FUNCTIONS = {
    "_ref_artifact_digest",
    "_verify_root_artifact",
    "_verify_host_runtime_artifact",
    "_validate_absolute_root_owned_chain_v1",
    "_runtime_path_is_under_v1",
    "_runtime_inclusion_paths_v1",
    "_derive_runtime_root_v1",
    "_probe_bootstrap_runtime_v1",
    "_validate_current_process_runtime_closure_v1",
    "_host_runtime_tree_entries_v1",
}
MOVED_SYMBOLS = MOVED_CONSTANTS | MOVED_FUNCTIONS


def _module_name(source_path: Path) -> str:
    parts = source_path.relative_to(PACKAGE_ROOT).with_suffix("").parts
    if parts == ("__init__",):
        return "semantic_guard_u10_broker"
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return "semantic_guard_u10_broker." + ".".join(parts)


def _module_trees() -> dict[str, ast.Module]:
    return {
        _module_name(source_path): ast.parse(
            source_path.read_text(encoding="utf-8"),
            filename=str(source_path),
        )
        for source_path in sorted(PACKAGE_ROOT.rglob("*.py"))
    }


def _top_level_definitions(tree: ast.Module) -> set[str]:
    definitions: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definitions.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            definitions.update(
                target.id for target in targets if isinstance(target, ast.Name)
            )
    return definitions


def _runtime_closure_reexports(tree: ast.Module) -> set[str]:
    return {
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and node.level == 1
        and node.module == "runtime_closure"
        for alias in node.names
    }


def _internal_import_graph(
    trees: dict[str, ast.Module],
) -> dict[str, set[str]]:
    graph = {module: set() for module in trees}
    for module, tree in trees.items():
        package = (
            module
            if module == "semantic_guard_u10_broker"
            else module.rsplit(".", 1)[0]
        )
        for node in ast.walk(tree):
            candidates: list[str] = []
            if isinstance(node, ast.Import):
                candidates.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    package_parts = package.split(".")
                    base = ".".join(
                        package_parts[: len(package_parts) - (node.level - 1)]
                    )
                    imported = (
                        f"{base}.{node.module}" if node.module else base
                    )
                else:
                    imported = node.module or ""
                candidates.append(imported)
                candidates.extend(
                    f"{imported}.{alias.name}"
                    for alias in node.names
                    if alias.name != "*"
                )
            graph[module].update(
                candidate for candidate in candidates if candidate in trees
            )
    return graph


def _cyclic_strongly_connected_components(
    graph: dict[str, set[str]],
) -> list[set[str]]:
    next_index = 0
    indices: dict[str, int] = {}
    low_links: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    cyclic_components: list[set[str]] = []

    def visit(module: str) -> None:
        nonlocal next_index
        indices[module] = next_index
        low_links[module] = next_index
        next_index += 1
        stack.append(module)
        on_stack.add(module)

        for dependency in graph[module]:
            if dependency not in indices:
                visit(dependency)
                low_links[module] = min(
                    low_links[module],
                    low_links[dependency],
                )
            elif dependency in on_stack:
                low_links[module] = min(
                    low_links[module],
                    indices[dependency],
                )

        if low_links[module] != indices[module]:
            return
        component: set[str] = set()
        while True:
            member = stack.pop()
            on_stack.remove(member)
            component.add(member)
            if member == module:
                break
        if len(component) > 1 or module in graph[module]:
            cyclic_components.append(component)

    for module in graph:
        if module not in indices:
            visit(module)
    return cyclic_components


class U10RuntimeClosureLayoutTests(unittest.TestCase):
    def test_core_names_are_runtime_closure_objects_by_identity(self) -> None:
        for name in MOVED_SYMBOLS:
            with self.subTest(name=name):
                self.assertIs(
                    getattr(core, name),
                    getattr(runtime_closure, name),
                )

    def test_runtime_closure_owns_exact_moved_symbols(self) -> None:
        trees = _module_trees()
        core_definitions = _top_level_definitions(trees[CORE_MODULE])
        runtime_definitions = _top_level_definitions(
            trees[RUNTIME_CLOSURE_MODULE]
        )

        self.assertEqual(core_definitions & MOVED_SYMBOLS, set())
        self.assertEqual(runtime_definitions & MOVED_SYMBOLS, MOVED_SYMBOLS)
        self.assertEqual(
            _runtime_closure_reexports(trees[CORE_MODULE]),
            MOVED_SYMBOLS,
        )
        self.assertIn(
            "_validate_bootstrap_runtime_manifest_v1",
            core_definitions,
        )
        self.assertNotIn(
            "_validate_bootstrap_runtime_manifest_v1",
            runtime_definitions,
        )

    def test_runtime_closure_dependency_direction_is_one_way(self) -> None:
        graph = _internal_import_graph(_module_trees())

        self.assertEqual(
            graph[RUNTIME_CLOSURE_MODULE],
            {PROTECTED_IO_MODULE, DARWIN_ACL_MODULE},
        )
        self.assertIn(RUNTIME_CLOSURE_MODULE, graph[CORE_MODULE])
        self.assertNotIn(CORE_MODULE, graph[RUNTIME_CLOSURE_MODULE])

    def test_u10_broker_ast_import_graph_has_zero_cyclic_sccs(self) -> None:
        graph = _internal_import_graph(_module_trees())

        self.assertEqual(_cyclic_strongly_connected_components(graph), [])


if __name__ == "__main__":
    unittest.main()
