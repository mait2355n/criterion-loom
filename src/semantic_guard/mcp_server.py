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
from .direction_binding_audit import audit_direction_binding
from .engine import audit_requirement_relations
from .japanese_dependency import GinzaDependencyProvider
from .japanese_morphology import SudachiMorphologyProvider
from .llm_candidates import SubmittedLLMCandidateProvider
from .legacy_runner import run_legacy_request, validate_requirement_input_size
from .public_contract import load_public_schema, public_audit_payload, validate_public_audit
from .shadow import compare_with_legacy


mcp = FastMCP("semantic-guard", json_response=True)

LEGACY_SHADOW_ENABLE_ENV = "SEMANTIC_GUARD_ENABLE_LEGACY_SHADOW"
LEGACY_SHADOW_ROOT_ENV = "SEMANTIC_GUARD_LEGACY_ROOT"
# Historical archive-relative locators retain the predecessor's ``vnext``
# subtree.  They are not canonical v1 package or public-contract names.
_LEGACY_BASELINE = Path("vnext/migration/legacy-baseline-2026-07-17.json")
_LEGACY_ADAPTER = Path("vnext/scripts/legacy_request_adapter.py")
_LEGACY_BASELINE_SHA256 = "df7acb77fe03495d11e82dff44b4674ae020bab852da7f706bc86c55a8d53fe4"
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
    output: str = "public",
) -> dict[str, Any]:
    validate_requirement_input_size(text)
    morphology_provider, dependency_provider = _providers(morphology, dependency)
    llm_provider = _llm_provider(llm_candidate_bundle)
    report = audit_requirement_relations(
        text,
        analysis_mode=analysis_mode,
        morphology_provider=morphology_provider,
        dependency_provider=dependency_provider,
        llm_provider=llm_provider,
    )
    if output == "legacy-compat":
        return project_legacy_result(report)
    if output == "assurance-v1":
        return public_assurance_claim_v1(report)
    if output != "public":
        raise ValueError("output must be public, assurance-v1, or legacy-compat")
    payload = public_audit_payload(report)
    validate_public_audit(payload)
    return payload


@mcp.tool()
def audit_requirement_relations_tool(
    text: str,
    analysis_mode: str = "assurance",
    morphology: str = "none",
    dependency: str = "none",
    llm_candidate_bundle: dict[str, Any] | None = None,
    output: str = "public",
) -> dict[str, Any]:
    """Audit a structured functional requirement with fail-closed obligation states.

    Provider choices are explicit.  Parser and LLM candidates never acquire
    support or hold-mutation authority merely by being selected. The optional
    assurance-v1 output wraps the validated public audit in a replayable proof
    graph; it is not human acceptance.
    """

    return audit_requirement_relations_service(
        text,
        analysis_mode=analysis_mode,
        morphology=morphology,
        dependency=dependency,
        llm_candidate_bundle=llm_candidate_bundle,
        output=output,
    )


def audit_direction_binding_service(
    text: str,
    *,
    context: str = "",
    morphology: str = "none",
    recorded_at: str | None = None,
) -> dict[str, Any]:
    """Run the independent direction-binding audit without changing v1 obligations."""

    if morphology not in {"none", "sudachi"}:
        raise ValueError("morphology must be none or sudachi")
    provider = SudachiMorphologyProvider() if morphology == "sudachi" else None
    return audit_direction_binding(
        text,
        context=context,
        morphology_provider=provider,
        recorded_at=recorded_at,
    )


@mcp.tool()
def audit_direction_binding_tool(
    text: str,
    context: str = "",
    morphology: str = "none",
    recorded_at: str | None = None,
) -> dict[str, Any]:
    """Audit whether one direction-open expression has a directly bound direction.

    Morphology is signal-only. Numeric witnesses cannot change the primary
    evaluation, and machine workflow pass is not human acceptance.
    """

    return audit_direction_binding_service(
        text,
        context=context,
        morphology=morphology,
        recorded_at=recorded_at,
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
        raise ValueError(f"LLM candidate bundle is not JSON serializable: {exc}") from exc
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
        raise RuntimeError("legacy interpreter .venv/bin/python is unavailable or not executable")
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
        raise RuntimeError(f"{label} resolves outside the configured legacy root") from exc
    if not resolved.is_file():
        raise RuntimeError(f"{label} must be a regular file")
    return resolved


@mcp.tool()
def shadow_compare_legacy_tool(
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
    report = audit_requirement_relations(
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
    return {
        "schema_version": "semantic-guard-shadow-run/v0",
        "canonical": native,
        "legacy": legacy.as_dict(),
        "comparison": compare_with_legacy(report, legacy).as_dict(),
    }


@mcp.tool()
def semantic_guard_schema_tool(name: str = "audit-result") -> dict[str, Any]:
    """Return one closed v1 JSON Schema by its public contract name."""

    return load_public_schema(name)


@mcp.resource(
    "semantic-guard://schemas/{name}",
    name="semantic-guard-schema",
    description="One closed semantic-guard v1 JSON Schema.",
    mime_type="application/schema+json",
)
def semantic_guard_schema_resource(name: str) -> str:
    return json.dumps(load_public_schema(name), ensure_ascii=False, sort_keys=True)


@mcp.resource(
    "semantic-guard://constitution/v1",
    name="semantic-guard-constitution",
    description="The canonical semantic-guard v1 constitution.",
    mime_type="application/yaml",
)
def semantic_guard_constitution_resource() -> str:
    package_candidate = resources.files("semantic_guard").joinpath(
        "constitution/semantic-guard-constitution.yaml"
    )
    if package_candidate.is_file():
        return package_candidate.read_text(encoding="utf-8")
    source_candidate = (
        Path(__file__).resolve().parents[2]
        / "constitution"
        / "semantic-guard-constitution.yaml"
    )
    return source_candidate.read_text(encoding="utf-8")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
