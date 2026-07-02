from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from semantic_guard.acceptance_review import acceptance_review_bundle_schema_path
from semantic_guard.conventions import conventions_catalog_path, conventions_dir_path, load_conventions_catalog
from semantic_guard.evaluation import DEFAULT_FIXTURE_ROOT, evaluate_fixture_tree
from semantic_guard.llm_review import candidate_gap_review_schema_path
from semantic_guard.models import audit_result_schema_path
from semantic_guard.rule_mapping import rule_detector_mappings, unmapped_rule_ids


Status = str


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: Status
    message: str
    details: dict[str, object] | None = None

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"name": self.name, "status": self.status, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


def run_doctor(project_root: str | Path = ".", *, run_fixtures: bool = True) -> dict[str, object]:
    root = Path(project_root).resolve()
    checks = [
        _check_python_version(),
        _check_project_files(root),
        _check_schemas(),
        _check_conventions(root),
        _check_mcp_dependency(),
        _check_codex_binary(),
        _check_rule_detector_mapping(),
        _check_ci_workflow(root),
    ]
    if run_fixtures:
        checks.append(_check_fixtures(root))

    status = _aggregate_status(check.status for check in checks)
    return {
        "phase": "doctor",
        "status": status,
        "checks": [check.as_dict() for check in checks],
        "summary": {
            "pass": sum(1 for check in checks if check.status == "pass"),
            "warn": sum(1 for check in checks if check.status == "warn"),
            "block": sum(1 for check in checks if check.status == "block"),
        },
        "next_actions": [check.message for check in checks if check.status != "pass"],
    }


def _check_python_version() -> DoctorCheck:
    version = sys.version_info
    if version >= (3, 11):
        return DoctorCheck("python_version", "pass", f"Python {version.major}.{version.minor}.{version.micro} satisfies >=3.11.")
    return DoctorCheck("python_version", "block", f"Python {version.major}.{version.minor}.{version.micro} is below >=3.11.")


def _check_project_files(root: Path) -> DoctorCheck:
    required = ["pyproject.toml", "README.md", "src/semantic_guard", "tests/fixtures"]
    missing = [item for item in required if not (root / item).exists()]
    if missing:
        package_resources = [audit_result_schema_path(), conventions_catalog_path(), DEFAULT_FIXTURE_ROOT]
        package_source_root = Path(__file__).resolve().parents[2]
        running_from_source_checkout = (package_source_root / "pyproject.toml").exists() and (
            package_source_root / "src" / "semantic_guard"
        ).exists()
        if not running_from_source_checkout and all(path.exists() for path in package_resources):
            return DoctorCheck(
                "project_files",
                "warn",
                "Source checkout files are missing, but installed package resources are present.",
                {"missing": missing, "mode": "installed_package"},
            )
        return DoctorCheck("project_files", "block", "Required project files are missing.", {"missing": missing})
    return DoctorCheck("project_files", "pass", "Required project files are present.")


def _check_schemas() -> DoctorCheck:
    schema_paths = [
        audit_result_schema_path(),
        candidate_gap_review_schema_path(),
        acceptance_review_bundle_schema_path(),
    ]
    missing: list[str] = []
    invalid: list[str] = []
    for path in schema_paths:
        if not path.exists():
            missing.append(str(path))
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            invalid.append(str(path))
    if missing or invalid:
        return DoctorCheck("schemas", "block", "Schema files are missing or invalid JSON.", {"missing": missing, "invalid": invalid})
    return DoctorCheck("schemas", "pass", "Schema files are present and parse as JSON.")


def _check_conventions(root: Path) -> DoctorCheck:
    checkout_directory = root / "docs" / "conventions"
    directory = checkout_directory if checkout_directory.exists() else conventions_dir_path()
    required = [directory / "README.md", directory / "base-contract.md", conventions_catalog_path()]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        return DoctorCheck("conventions", "warn", "Convention documents are missing.", {"missing": missing})
    try:
        catalog = load_conventions_catalog()
    except (OSError, json.JSONDecodeError) as exc:
        return DoctorCheck("conventions", "block", "Convention catalog cannot be loaded.", {"error": str(exc)})
    if catalog.get("schema_version") != "semantic-guard-conventions/v1":
        return DoctorCheck("conventions", "block", "Convention catalog has an unexpected schema_version.", {"schema_version": catalog.get("schema_version")})
    rules = catalog.get("rules", [])
    if not isinstance(rules, list) or not rules:
        return DoctorCheck("conventions", "block", "Convention catalog has no rules.")
    return DoctorCheck(
        "conventions",
        "pass",
        "Convention documents and machine-readable catalog are present.",
        {"catalog": str(conventions_catalog_path()), "rule_count": len(rules), "status": catalog.get("status")},
    )


def _check_mcp_dependency() -> DoctorCheck:
    try:
        import mcp.server.fastmcp  # noqa: F401
    except Exception as exc:  # pragma: no cover - exact import failures are environment dependent
        return DoctorCheck("mcp_dependency", "block", "mcp.server.fastmcp could not be imported.", {"error": str(exc)})
    return DoctorCheck("mcp_dependency", "pass", "mcp.server.fastmcp imports successfully.")


def _check_codex_binary(which: Callable[[str], str | None] = shutil.which) -> DoctorCheck:
    path = which("codex")
    if path:
        return DoctorCheck("codex_binary", "pass", "codex binary is available.", {"path": path})
    return DoctorCheck("codex_binary", "warn", "codex binary is not on PATH; LLM reviewer execution will not work here.")


def _check_rule_detector_mapping() -> DoctorCheck:
    unmapped = unmapped_rule_ids()
    if unmapped:
        return DoctorCheck("rule_detector_mapping", "block", "Some catalog rules do not have detector mappings.", {"unmapped_rule_ids": unmapped})
    return DoctorCheck(
        "rule_detector_mapping",
        "pass",
        "Every catalog rule has a detector mapping.",
        {"mapping_count": len(rule_detector_mappings())},
    )


def _check_ci_workflow(root: Path) -> DoctorCheck:
    workflow = root / ".github" / "workflows" / "ci.yml"
    if not workflow.exists():
        return DoctorCheck("ci_workflow", "warn", ".github/workflows/ci.yml is not present in this checkout.")
    text = workflow.read_text(encoding="utf-8")
    required_terms = ["compileall", "unittest discover", "evaluate-fixtures"]
    missing_terms = [term for term in required_terms if term not in text]
    if missing_terms:
        return DoctorCheck("ci_workflow", "warn", "CI workflow is present but missing expected verification commands.", {"missing_terms": missing_terms})
    return DoctorCheck("ci_workflow", "pass", "CI workflow includes compile, unit test, and fixture evaluation steps.")


def _check_fixtures(root: Path) -> DoctorCheck:
    fixture_root = root / "tests" / "fixtures"
    if not fixture_root.exists():
        fixture_root = DEFAULT_FIXTURE_ROOT
    result = evaluate_fixture_tree(fixture_root, include_passed=False)
    status = "pass" if result["failed"] == 0 and result["total"] > 0 else "block"
    return DoctorCheck(
        "fixtures",
        status,
        f"Fixture evaluation: {result['passed']}/{result['total']} passed.",
        {"total": result["total"], "passed": result["passed"], "failed": result["failed"], "pass_rate": result["pass_rate"]},
    )


def _aggregate_status(statuses: object) -> str:
    status_set = set(statuses)
    if "block" in status_set:
        return "block"
    if "warn" in status_set:
        return "warn"
    return "pass"
