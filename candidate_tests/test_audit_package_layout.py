from __future__ import annotations

import ast
from graphlib import CycleError, TopologicalSorter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest


PACKAGE_ROOT = (
    Path(__file__).resolve().parents[1] / "src" / "semantic_guard_vnext"
)
LEGACY_MODULES = {
    "semantic_guard_vnext.aggregation",
    "semantic_guard_vnext.engine",
    "semantic_guard_vnext.engine_stages",
}
ROOT_EXPORTS = [
    "AuditExecution",
    "Challenge",
    "Coverage",
    "DecisionRequest",
    "EvidenceRef",
    "EvidenceRole",
    "Finality",
    "GuardCoverage",
    "Hold",
    "ObligationResult",
    "Outcome",
    "RequirementAuditReport",
    "SourceSpan",
    "StageAuthority",
    "VNextAuditResult",
    "Workflow",
    "aggregate_audit_result",
    "audit_requirement_relations_vnext",
    "combined_challenge",
    "combined_coverage",
    "pass_invariants_hold",
    "load_public_schema",
    "public_audit_payload",
    "validate_public_audit",
]
COMPLETE = """Purpose: 検索APIが検索結果を p95 500ms以内で返す
User: 検索API
Scenario: 検索APIが検索要求を処理して検索結果を返す
Expected result: 検索結果を p95 500ms以内で返す
Acceptance criteria: 検索応答時間 p95 500ms 以下
Verification method: 検索結果の検索応答時間を benchmark で測定する
Evidence: 検索結果の検索応答時間 benchmark report"""
REPORT_SHA256 = "8952848f678f58a1ae65fbf6aedb3064a6d1816e28edd47414c0f92f5e721c09"
PUBLIC_SHA256 = "b17f5e3cfb8cefbc9bc9ed12ba66a066d7e2e09cc4487a856a8f688d6c544d15"


def _module_name(path: Path) -> str:
    parts = path.relative_to(PACKAGE_ROOT).with_suffix("").parts
    if parts == ("__init__",):
        return "semantic_guard_vnext"
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return "semantic_guard_vnext." + ".".join(parts)


def _internal_import_graph() -> dict[str, set[str]]:
    modules = {
        _module_name(path): path
        for path in sorted(PACKAGE_ROOT.rglob("*.py"))
    }
    graph = {module: set() for module in modules}
    for module, path in modules.items():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        package = module if path.name == "__init__.py" else module.rsplit(".", 1)[0]
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
                candidate for candidate in candidates if candidate in modules
            )
    return graph


def _fresh_import_state(statement: str) -> dict[str, bool]:
    code = (
        statement
        + "\n"
        + """
import json
import sys
print(json.dumps({
    "audit_engine": "semantic_guard_vnext.audit.engine" in sys.modules,
    "legacy_engine": "semantic_guard_vnext.engine" in sys.modules,
    "public_contract": "semantic_guard_vnext.public_contract" in sys.modules,
    "jsonschema": "jsonschema" in sys.modules,
}))
"""
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class AuditPackageLayoutTests(unittest.TestCase):
    def test_legacy_modules_reexport_canonical_objects_by_identity(self) -> None:
        from semantic_guard_vnext import aggregation as legacy_aggregation
        from semantic_guard_vnext import engine as legacy_engine
        from semantic_guard_vnext import engine_stages as legacy_stages
        from semantic_guard_vnext.audit import aggregation, engine, report, stages

        self.assertIs(
            legacy_aggregation.aggregate_audit_result,
            aggregation.aggregate_audit_result,
        )
        self.assertIs(
            legacy_engine.audit_requirement_relations_vnext,
            engine.audit_requirement_relations_vnext,
        )
        self.assertIs(legacy_engine.CATEGORY_GUARD, engine.CATEGORY_GUARD)
        self.assertIs(
            legacy_engine.RequirementAuditReport,
            report.RequirementAuditReport,
        )
        self.assertIs(
            legacy_stages.build_audit_execution,
            stages.build_audit_execution,
        )
        self.assertEqual(
            report.RequirementAuditReport.__module__,
            "semantic_guard_vnext.audit.report",
        )
        self.assertEqual(
            engine.audit_requirement_relations_vnext.__module__,
            "semantic_guard_vnext.audit.engine",
        )

    def test_root_facade_preserves_names_and_canonical_identity(self) -> None:
        import semantic_guard_vnext as root
        from semantic_guard_vnext.audit.aggregation import aggregate_audit_result
        from semantic_guard_vnext.audit.engine import (
            audit_requirement_relations_vnext,
        )
        from semantic_guard_vnext.audit.report import RequirementAuditReport

        self.assertEqual(root.__all__, ROOT_EXPORTS)
        self.assertIs(root.aggregate_audit_result, aggregate_audit_result)
        self.assertIs(
            root.audit_requirement_relations_vnext,
            audit_requirement_relations_vnext,
        )
        self.assertIs(root.RequirementAuditReport, RequirementAuditReport)
        self.assertTrue(all(hasattr(root, name) for name in ROOT_EXPORTS))

    def test_root_and_leaf_imports_do_not_eagerly_load_audit_stack(self) -> None:
        expected = {
            "audit_engine": False,
            "legacy_engine": False,
            "public_contract": False,
            "jsonschema": False,
        }
        self.assertEqual(
            _fresh_import_state("import semantic_guard_vnext"),
            expected,
        )
        self.assertEqual(
            _fresh_import_state("import semantic_guard_vnext.models"),
            expected,
        )

    def test_internal_modules_do_not_depend_on_legacy_shims(self) -> None:
        graph = _internal_import_graph()
        references = sorted(
            (source, target)
            for source, targets in graph.items()
            if source not in LEGACY_MODULES
            for target in targets
            if target in LEGACY_MODULES
        )

        self.assertEqual(references, [])

    def test_internal_import_graph_has_no_cycle(self) -> None:
        graph = _internal_import_graph()
        sorter = TopologicalSorter(graph)
        try:
            sorter.prepare()
        except CycleError as error:
            self.fail(f"internal import cycle: {error.args}")

    def test_report_and_public_payload_match_pre_move_baseline(self) -> None:
        from semantic_guard_vnext.audit.engine import (
            audit_requirement_relations_vnext,
        )
        from semantic_guard_vnext.public_contract import (
            public_audit_payload,
            validate_public_audit,
        )

        report = audit_requirement_relations_vnext(
            COMPLETE,
            analysis_mode="conditional",
        )
        payload = public_audit_payload(
            report,
            recorded_at="2026-07-29T00:00:00Z",
        )
        validate_public_audit(payload)

        self.assertEqual(_canonical_digest(report.as_dict()), REPORT_SHA256)
        self.assertEqual(_canonical_digest(payload), PUBLIC_SHA256)


if __name__ == "__main__":
    unittest.main()
