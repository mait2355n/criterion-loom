from __future__ import annotations

from importlib import resources
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from mcp.server.fastmcp import FastMCP

from .assurance_graph import public_assurance_claim_v1
from .compat import project_legacy_result
from .audit.engine import audit_requirement_relations_vnext
from .governed_audit import project_governed_audit, wrap_legacy_output
from .governance_materials import default_candidate_governance_materials
from .japanese_dependency import GinzaDependencyProvider
from .japanese_morphology import SudachiMorphologyProvider
from .llm_candidates import SubmittedLLMCandidateProvider
from .legacy_runner import run_legacy_request, validate_requirement_input_size
from .legacy_shadow_observation import build_legacy_shadow_observation
from .public_contract import (
    load_public_schema,
    public_audit_payload,
    validate_public_audit,
)
from .shadow import compare_with_legacy


mcp = FastMCP("semantic-guard-vnext", json_response=True)

LEGACY_SHADOW_ENABLE_ENV = "SEMANTIC_GUARD_VNEXT_ENABLE_LEGACY_SHADOW"
LEGACY_SHADOW_ROOT_ENV = "SEMANTIC_GUARD_VNEXT_LEGACY_ROOT"
_LEGACY_BASELINE = Path("vnext/migration/legacy-baseline-2026-07-16.json")
_LEGACY_ADAPTER = Path("vnext/scripts/legacy_request_adapter.py")
_LEGACY_BASELINE_SHA256 = (
    "3f06828e9f544285dc2c4084698a05e03aa56fabaee8563bb9c4217cde352d46"
)
_MAX_SHADOW_TIMEOUT_SECONDS = 120.0
_MAX_LLM_CANDIDATE_BUNDLE_BYTES = 1_048_576


def _providers(morphology: str, dependency: str):
    if morphology not in {"none", "sudachi"}:
        raise ValueError("morphology must be none or sudachi")
    if dependency not in {"none", "ginza"}:
        raise ValueError("dependency must be none or ginza")
    return (
        SudachiMorphologyProvider() if morphology == "sudachi" else None,
        GinzaDependencyProvider() if dependency == "ginza" else None,
    )


def audit_requirement_relations_service(
    text: str,
    *,
    analysis_mode: str = "assurance",
    morphology: str = "none",
    dependency: str = "none",
    llm_candidate_bundle: dict[str, Any] | None = None,
    governance_materials: dict[str, Any] | None = None,
    output: str = "governed-v1",
) -> dict[str, Any]:
    validate_requirement_input_size(text)
    morphology_provider, dependency_provider = _providers(morphology, dependency)
    llm_provider = _llm_provider(llm_candidate_bundle)
    report = audit_requirement_relations_vnext(
        text,
        analysis_mode=analysis_mode,
        morphology_provider=morphology_provider,
        dependency_provider=dependency_provider,
        llm_provider=llm_provider,
    )
    if governance_materials is not None and output not in {"governed-v1", "public"}:
        raise ValueError(
            "governance_materials is valid only for governed-v1/public output"
        )
    if output == "legacy-compat":
        return wrap_legacy_output(output, project_legacy_result(report))
    if output == "legacy-assurance-v1":
        return wrap_legacy_output(output, public_assurance_claim_v1(report))
    if output == "legacy-internal-debug-v0":
        return wrap_legacy_output(output, report.as_dict())
    if output == "legacy-public-v0":
        legacy_payload = public_audit_payload(report)
        validate_public_audit(legacy_payload)
        return wrap_legacy_output(output, legacy_payload)
    if output in {"governed-v1", "public"}:
        effective_materials = default_candidate_governance_materials()
        if governance_materials is not None:
            effective_materials.update(governance_materials)
        return project_governed_audit(
            report,
            governance_materials=effective_materials,
        )
    raise ValueError(
        "output must be governed-v1, public, legacy-public-v0, "
        "legacy-assurance-v1, legacy-internal-debug-v0, or legacy-compat"
    )


@mcp.tool()
def audit_requirement_relations_vnext_tool(
    text: str,
    analysis_mode: str = "assurance",
    morphology: str = "none",
    dependency: str = "none",
    llm_candidate_bundle: dict[str, Any] | None = None,
    governance_materials: dict[str, Any] | None = None,
    output: str = "governed-v1",
) -> dict[str, Any]:
    """Audit a structured requirement with a governance-fail-closed default.

    The default records legacy v0 analysis only as an observation, adapts the
    pinned real H1/H2 documents as untrusted candidates, and retains every
    result below formal verdict authority while H1, H2, ENV-PATH, and D7 remain
    unresolved.
    ``legacy-public-v0`` is an explicit compatibility observation, not current
    engineering assurance. ``legacy-assurance-v1`` is likewise a historical
    internal-closure projection and never current engineering assurance.
    Every legacy format is returned only inside a self-describing ungoverned,
    observation-only envelope with the old value nested as ``legacy_payload``.
    No output is human acceptance.
    """

    return audit_requirement_relations_service(
        text,
        analysis_mode=analysis_mode,
        morphology=morphology,
        dependency=dependency,
        llm_candidate_bundle=llm_candidate_bundle,
        governance_materials=governance_materials,
        output=output,
    )


def _llm_provider(
    bundle: dict[str, Any] | None,
) -> SubmittedLLMCandidateProvider | None:
    if bundle is None:
        return None
    try:
        encoded = json.dumps(bundle, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"LLM candidate bundle is not JSON serializable: {exc}"
        ) from exc
    if len(encoded) > _MAX_LLM_CANDIDATE_BUNDLE_BYTES:
        raise ValueError(
            "LLM candidate bundle exceeds "
            f"{_MAX_LLM_CANDIDATE_BUNDLE_BYTES} UTF-8 bytes"
        )
    return SubmittedLLMCandidateProvider(bundle)


def _fixed_legacy_shadow_paths(
    environ: Mapping[str, str] | None = None,
) -> tuple[Path, Path, Path]:
    """Resolve operator-owned legacy paths without accepting tool-supplied paths."""

    values = os.environ if environ is None else environ
    if values.get(LEGACY_SHADOW_ENABLE_ENV) != "1":
        raise RuntimeError(
            "legacy shadow comparison is disabled; the MCP server operator must set "
            f"{LEGACY_SHADOW_ENABLE_ENV}=1"
        )
    configured_root = values.get(LEGACY_SHADOW_ROOT_ENV, "")
    root_path = Path(configured_root)
    if not configured_root or not root_path.is_absolute():
        raise RuntimeError(
            f"{LEGACY_SHADOW_ROOT_ENV} must be an absolute legacy source root"
        )
    try:
        root = root_path.resolve(strict=True)
    except OSError as exc:
        raise RuntimeError(f"legacy source root is unavailable: {exc}") from exc
    if not root.is_dir():
        raise RuntimeError("legacy source root must be a directory")

    baseline = _fixed_descendant(root, _LEGACY_BASELINE, "baseline manifest")
    adapter = _fixed_descendant(root, _LEGACY_ADAPTER, "legacy adapter")
    baseline_digest = hashlib.sha256(baseline.read_bytes()).hexdigest()
    if baseline_digest != _LEGACY_BASELINE_SHA256:
        raise RuntimeError(
            "legacy baseline manifest digest does not match the server-pinned migration baseline"
        )
    interpreter = root / ".venv" / "bin" / "python"
    if not interpreter.is_file() or not os.access(interpreter, os.X_OK):
        raise RuntimeError(
            "legacy interpreter .venv/bin/python is unavailable or not executable"
        )
    return root, baseline, adapter


def _fixed_descendant(root: Path, relative: Path, label: str) -> Path:
    candidate = root / relative
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise RuntimeError(f"{label} is unavailable: {exc}") from exc
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise RuntimeError(
            f"{label} resolves outside the configured legacy root"
        ) from exc
    if not resolved.is_file():
        raise RuntimeError(f"{label} must be a regular file")
    return resolved


@mcp.tool()
def shadow_compare_legacy_vnext_tool(
    text: str,
    analysis_mode: str = "shadow_all",
    morphology: str = "none",
    dependency: str = "none",
    llm_candidate_bundle: dict[str, Any] | None = None,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    """Observe an operator-pinned legacy process and classify, but do not auto-resolve, deltas.

    This tool is disabled unless the server operator explicitly enables it and
    supplies one absolute legacy root through process environment.  Tool
    callers cannot select an executable, adapter, manifest, or filesystem root.
    """

    validate_requirement_input_size(text)
    if not 0.1 <= timeout_seconds <= _MAX_SHADOW_TIMEOUT_SECONDS:
        raise ValueError(
            f"timeout_seconds must be between 0.1 and {_MAX_SHADOW_TIMEOUT_SECONDS}"
        )
    root, baseline, adapter = _fixed_legacy_shadow_paths()
    morphology_provider, dependency_provider = _providers(morphology, dependency)
    llm_provider = _llm_provider(llm_candidate_bundle)
    report = audit_requirement_relations_vnext(
        text,
        analysis_mode=analysis_mode,
        morphology_provider=morphology_provider,
        dependency_provider=dependency_provider,
        llm_provider=llm_provider,
    )
    legacy = run_legacy_request(
        text=text,
        legacy_root=root,
        baseline_manifest=baseline,
        adapter_script=adapter,
        timeout_seconds=timeout_seconds,
    )
    native = public_audit_payload(report)
    validate_public_audit(native)
    return build_legacy_shadow_observation(
        vnext=native,
        legacy=legacy.as_dict(),
        comparison=compare_with_legacy(report, legacy).as_dict(),
    )


@mcp.tool()
def semantic_guard_vnext_schema_tool(name: str = "audit-result") -> dict[str, Any]:
    """Return one closed vNext JSON Schema by its public contract name."""

    return load_public_schema(name)


@mcp.resource(
    "semantic-guard://schemas/{name}",
    name="semantic-guard-vnext-schema",
    description="One closed semantic-guard vNext JSON Schema.",
    mime_type="application/schema+json",
)
def semantic_guard_vnext_schema_resource(name: str) -> str:
    return json.dumps(load_public_schema(name), ensure_ascii=False, sort_keys=True)


@mcp.resource(
    "semantic-guard://constitution/vnext",
    name="semantic-guard-vnext-constitution",
    description="The candidate semantic-guard vNext constitution.",
    mime_type="application/yaml",
)
def semantic_guard_vnext_constitution_resource() -> str:
    package_candidate = resources.files("semantic_guard_vnext").joinpath(
        "constitution/semantic-guard-vnext-constitution.yaml"
    )
    return package_candidate.read_text(encoding="utf-8")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
