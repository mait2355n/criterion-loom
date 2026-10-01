#!/usr/bin/env python3
"""Verify canonical, workflow and candidate contracts from one installed wheel.

The verifier installs one local wheel into a fresh temporary virtual
environment, plants controlled decoy resources beside site-packages, and runs
a fixed audit program with isolated Python path handling.  It never accepts an
alternate Python executable, audit program, or resource directory from the
caller.

The wheel itself is necessarily imported by the audit process.  This is a
distribution-integrity check, not an operating-system sandbox for untrusted
code.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
from pathlib import PurePosixPath
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from typing import Any, Mapping, Sequence
import zipfile


SCHEMA_VERSION = "semantic-guard-packaged-contract-verification/v0"
DEFAULT_TIMEOUT_SECONDS = 180.0
MIN_TIMEOUT_SECONDS = 15.0
MAX_TIMEOUT_SECONDS = 300.0
MAX_WHEEL_BYTES = 64 * 1024 * 1024
MAX_WHEEL_ENTRIES = 4096
MAX_WHEEL_UNCOMPRESSED_BYTES = 256 * 1024 * 1024
MAX_SDIST_BYTES = 64 * 1024 * 1024
MAX_SDIST_ENTRIES = 4096
MAX_SDIST_UNCOMPRESSED_BYTES = 256 * 1024 * 1024
MAX_CAPTURE_BYTES = 1024 * 1024
MAX_CHILD_FILE_BYTES = 256 * 1024 * 1024
MAX_CHILD_ADDRESS_SPACE_BYTES = 4 * 1024 * 1024 * 1024
MAX_CHILD_OPEN_FILES = 256

_ALLOWED_PACKAGED_VALIDATION_FILES = frozenset(
    {
        "engineering-rule-pack.candidate.json",
        "engineering-rule-pack.schema.json",
        "lifecycle-profile-registry.candidate.json",
    }
)
_ALLOWED_SDIST_ROOTS = frozenset(
    {
        ".gitignore",
        "LICENSE",
        "PKG-INFO",
        "README.md",
        "constitution",
        "pyproject.toml",
        "schemas",
        "src",
        "validation",
    }
)
_CANONICAL_SDIST_ROOT = "semantic_guard-1.2.0.dev0"
_RUNTIME_NAMESPACES = frozenset({
    "semantic_guard", "semantic_guard_workflow", "semantic_guard_vnext",
    "semantic_guard_u10_broker",
})
_CANONICAL_WHEEL_ROOTS = _RUNTIME_NAMESPACES | {"semantic_guard-1.2.0.dev0.dist-info"}
_CONSOLE_ENTRYPOINTS = frozenset({
    "semantic-guard", "semantic-guard-mcp",
    "semantic-guard-workflow", "semantic-guard-workflow-mcp",
    "semantic-guard-vnext", "semantic-guard-vnext-mcp",
})

# Deliberately fixed at this integration candidate; never inferred from the
# wheel being checked or caller-selected metadata.
_ALLOWED_ADDITIONAL_RESOURCES = frozenset({
    'semantic_guard_vnext/constitution/semantic-guard-vnext-constitution.yaml',
    'semantic_guard_vnext/schemas/action-assurance-profile.schema.json',
    'semantic_guard_vnext/schemas/action-evidence.schema.json',
    'semantic_guard_vnext/schemas/analysis-provider.schema.json',
    'semantic_guard_vnext/schemas/assurance-claim-v1.schema.json',
    'semantic_guard_vnext/schemas/assurance-claim.schema.json',
    'semantic_guard_vnext/schemas/assurance-role-binding.schema.json',
    'semantic_guard_vnext/schemas/audit-result.schema.json',
    'semantic_guard_vnext/schemas/candidate-governance-adapters.schema.json',
    'semantic_guard_vnext/schemas/common.schema.json',
    'semantic_guard_vnext/schemas/decision-request.schema.json',
    'semantic_guard_vnext/schemas/engineering-rule-governance-v1.schema.json',
    'semantic_guard_vnext/schemas/evidence-validity-policy.schema.json',
    'semantic_guard_vnext/schemas/field-evaluation.schema.json',
    'semantic_guard_vnext/schemas/field-performance-governance.schema.json',
    'semantic_guard_vnext/schemas/governance-material-assessment.schema.json',
    'semantic_guard_vnext/schemas/governed-audit-result.schema.json',
    'semantic_guard_vnext/schemas/legacy-output-envelope.schema.json',
    'semantic_guard_vnext/schemas/legacy-shadow-observation-envelope.schema.json',
    'semantic_guard_vnext/schemas/lifecycle-governance-v1.schema.json',
    'semantic_guard_vnext/schemas/lifecycle-profile-registry.schema.json',
    'semantic_guard_vnext/schemas/lifecycle-trace.schema.json',
    'semantic_guard_vnext/schemas/llm-candidate-input.schema.json',
    'semantic_guard_vnext/schemas/obligation-result.schema.json',
    'semantic_guard_vnext/schemas/operational-outcome-evaluation.schema.json',
    'semantic_guard_vnext/schemas/operational-qualification.schema.json',
    'semantic_guard_vnext/schemas/repair-cycle.schema.json',
    'semantic_guard_vnext/schemas/responsibility-material.schema.json',
    'semantic_guard_vnext/schemas/responsibility-policy.schema.json',
    'semantic_guard_vnext/schemas/secure-operation.schema.json',
    'semantic_guard_vnext/schemas/state-assessment.schema.json',
    'semantic_guard_vnext/schemas/subject-manifest.schema.json',
    'semantic_guard_vnext/schemas/transition-plan.schema.json',
    'semantic_guard_vnext/validation/engineering-rule-pack.candidate.json',
    'semantic_guard_vnext/validation/engineering-rule-pack.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/broker-attested-execution-envelope-v2.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/broker-attested-execution-envelope-v3.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/closed-verification-test-manifest-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/environment-eligibility-resolution-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/environment-eligibility-source-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/governed-environment-execution-receipt-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/local-environment-adoption-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/local-environment-adoption.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/local-environment-snapshot-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/local-host-identity-evidence-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/local-verification-profile-v3.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/local-verification-profile-v4.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/process-containment-probe-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/resolved-local-environment-profile-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/resolved-local-environment-profile.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-bootstrap-provenance-binding-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-bootstrap-provisioning-authorization-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-bootstrap-provisioning-consumption-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-bootstrap-provisioning-plan-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-bootstrap-provisioning-receipt-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-bootstrap-runtime-manifest-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-bootstrap-runtime-observation-receipt-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-bootstrap-runtime-observation-request-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-candidate-install-authorization-consumption-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-candidate-install-authorization-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-candidate-install-projection-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-candidate-install-receipt-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-candidate-install-receipt-v2.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-control-publisher-contract-binding-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-control-runtime-manifest-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-execution-request-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-execution-snapshot-manifest-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-initial-bootstrap-capsule-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-key-operation-authorization-consumption-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-key-operation-authorization-consumption-v2.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-key-operation-authorization-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-key-operation-authorization-v2.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-key-operation-receipt-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-key-operation-receipt-v2.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-key-transition-emergency-closure-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-preactivation-decision-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-root-candidate-bundle-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-root-trust-store-v2.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-signing-key-metadata-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-signing-key-metadata-v2.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-signing-key-revocation-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-signing-key-revocation-v2.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-signing-key-selector-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-signing-key-selector-v2.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-snapshot-activation-authorization-consumption-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-snapshot-activation-basis-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-snapshot-activation-publication-receipt-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-snapshot-activation-record-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-snapshot-adoption-authorization-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-snapshot-environment-adoption-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-snapshot-projection-authorization-consumption-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-snapshot-projection-authorization-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-snapshot-projection-receipt-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-store-activation-authorization-consumption-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-store-activation-authorization-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-store-activation-basis-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-store-activation-basis-v2.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-store-activation-transition-receipt-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-store-activation-transition-receipt-v2.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-store-revocation-authorization-consumption-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-store-revocation-publication-receipt-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-store-revocation-publication-receipt-v2.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-store-revocation-record-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-worker-account-observation-v1.schema.json',
    'semantic_guard_vnext/validation/env-path-contracts/u10-worker-principal-resolution-v1.schema.json',
    'semantic_guard_vnext/validation/lifecycle-profile-registry.candidate.json',
    'semantic_guard_vnext/validation/local-environment-snapshot.schema.json',
    'semantic_guard_vnext/validation/local-verification-profile-v1.schema.json',
    'semantic_guard_vnext/validation/local-verification-profile-v2.schema.json',
    'semantic_guard_vnext/validation/local-verification-profile.schema.json',
    'semantic_guard_vnext/validation/local-verification-run-v1.schema.json',
    'semantic_guard_vnext/validation/local-verification-run-v2.schema.json',
    'semantic_guard_vnext/validation/local-verification-run.schema.json',
    'semantic_guard_workflow/_resources/docs/conventions/README.md',
    'semantic_guard_workflow/_resources/docs/conventions/base-contract.json',
    'semantic_guard_workflow/_resources/docs/conventions/base-contract.md',
    'semantic_guard_workflow/_resources/schemas/acceptance-review-bundle.schema.json',
    'semantic_guard_workflow/_resources/schemas/audit-result.schema.json',
    'semantic_guard_workflow/_resources/schemas/candidate-gap-review.schema.json',
    'semantic_guard_workflow/_resources/schemas/request-exploration-review.schema.json',
    'semantic_guard_workflow/_resources/tests/fixtures/conflicts/c01-bounded-whole-plan.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/conflicts/c02-bounded-work-package-request.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/conflicts/c07-docs-only-evidence-diff.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/diffs/command-defaults.diff',
    'semantic_guard_workflow/_resources/tests/fixtures/diffs/command-defaults.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/diffs/complexity-growth.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/diffs/dependency-runtime-change.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/diffs/failure-handling-missing.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/diffs/field-test-command-no-contract.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/diffs/filename-content-overbreadth.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/diffs/filename-scope-underspecified.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/diffs/identity-boundary-change.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/diffs/operational-observability-missing.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/diffs/public-contract-change.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/diffs/source-without-tests.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/diffs/subprocess-security.diff',
    'semantic_guard_workflow/_resources/tests/fixtures/diffs/subprocess-security.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/documents/overclaim.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/documents/overclaim.md',
    'semantic_guard_workflow/_resources/tests/fixtures/documents/readme-good.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/documents/readme-good.md',
    'semantic_guard_workflow/_resources/tests/fixtures/finish/no-evidence.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/finish/no-evidence.md',
    'semantic_guard_workflow/_resources/tests/fixtures/finish/public-behavior-good.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/finish/public-behavior-missing.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/plans/autonomy-permission-question-good.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/plans/autonomy-question-necessity-missing.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/plans/field-rollback-missing.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/plans/good.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/plans/good.md',
    'semantic_guard_workflow/_resources/tests/fixtures/plans/hazard-transfer-good.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/plans/hazard-transfer-missing.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/plans/idempotency-missing.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/plans/minimality-justification-missing.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/plans/problem-fit-missing.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/plans/progress-control-missing.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/plans/release-good.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/plans/release-provenance-missing.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/plans/release-weak.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/plans/rollback-missing.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/plans/validation-owner-missing.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/requests/achievement-criteria-missing.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/requests/ambiguous.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/requests/ambiguous.md',
    'semantic_guard_workflow/_resources/tests/fixtures/requests/decision-frame-direction-unbound-with-impact.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/requests/decision-frame-morphology-disabled.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/requests/decision-frame-order-direction-unspecified.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/requests/detailed-search.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/requests/evidence-artifact-missing.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/requests/field-priority-unprioritized.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/requests/interface-contract-missing.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/requests/negated-assurance-fields.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/requests/observable-behavior-missing.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/requests/priority-missing.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/requests/problem-mechanism-fit-good.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/requests/problem-mechanism-fit-missing.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/requests/rejection-condition-missing.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/requests/scenario-context-missing.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/requests/stakeholder-source-missing.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/requests/structured-negated-assurance-fields.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/requests/uncertainty-classified-good.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/requests/uncertainty-unclassified.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/requests/verification-method-weak.expected.json',
    'semantic_guard_workflow/_resources/tests/fixtures/requests/verification-target-mismatch.expected.json',
})


_AUDIT_PROGRAM = r'''
from __future__ import annotations

import argparse
import asyncio
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib.util
from importlib import resources
from importlib.metadata import distribution
import io
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, FormatChecker


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


spec = importlib.util.find_spec("semantic_guard")
require(spec is not None and spec.submodule_search_locations, "installed package not found")
package_root = Path(tuple(spec.submodule_search_locations)[0]).resolve()
prefix = Path(sys.prefix).resolve()
try:
    package_root.relative_to(prefix)
except ValueError as exc:
    raise RuntimeError("semantic_guard was not imported from the isolated environment") from exc

# These locations reproduce the accidental source-tree fallbacks that an
# installed module could otherwise derive through Path(__file__).parents[2].
adjacent_root = package_root.parents[1]
decoy_validation = adjacent_root / "validation"
decoy_schemas = adjacent_root / "schemas"
decoy_validation.mkdir()
decoy_schemas.mkdir()
(adjacent_root / "pyproject.toml").write_text(
    "[project]\nname = 'decoy-neighbour'\nversion = '0'\n",
    encoding="utf-8",
)
(decoy_validation / "lifecycle-profile-registry.candidate.json").write_text(
    json.dumps({"schema_version": "decoy-lifecycle-profile/v0"}),
    encoding="utf-8",
)
(decoy_schemas / "operational-outcome-evaluation.schema.json").write_text(
    "{}\n",
    encoding="utf-8",
)
# Cover current-directory lookup as well as module-relative lookup. These
# permissive schemas must never become any namespace's selected resources.
for decoy_root in (adjacent_root, Path.cwd()):
    (decoy_root / "schemas").mkdir(exist_ok=True)
    (decoy_root / "validation").mkdir(exist_ok=True)
    for name in ("audit-result", "common", "governed-audit-result"):
        (decoy_root / "schemas" / (name + ".schema.json")).write_text("{}\n")
    (decoy_root / "validation" / "engineering-rule-pack.candidate.json").write_text("{}\n")

from semantic_guard import __version__, lifecycle_profiles
from semantic_guard import operational_outcomes
from semantic_guard.cli import build_parser
from semantic_guard.lifecycle_profiles import (
    load_candidate_registry,
    validate_lifecycle_profile_registry,
)
from semantic_guard.mcp_server import (
    audit_direction_binding_service,
    audit_requirement_relations_service,
    mcp,
    semantic_guard_schema_resource,
)
from semantic_guard.public_contract import KNOWN_SCHEMA_NAMES, load_public_schema
from semantic_guard.schema_access import schema_directory

installed_distribution = distribution("semantic-guard")
require(
    installed_distribution.metadata["Name"] == "semantic-guard",
    "installed distribution name is not canonical",
)
require(installed_distribution.version == "1.2.0.dev0", "installed distribution is not v1.2.0.dev0")
require(__version__ == installed_distribution.version, "package and distribution versions differ")
require(
    {item.name for item in installed_distribution.entry_points if item.group == "console_scripts"}
    == {"semantic-guard", "semantic-guard-mcp", "semantic-guard-workflow",
        "semantic-guard-workflow-mcp", "semantic-guard-vnext", "semantic-guard-vnext-mcp"},
    "distribution console entrypoints are not the six explicit routes",
)
require(mcp.name == "semantic-guard", "MCP server name is not canonical")
mcp_tools = asyncio.run(mcp.list_tools())
mcp_resources = asyncio.run(mcp.list_resources())
mcp_resource_templates = asyncio.run(mcp.list_resource_templates())
require(
    {tool.name for tool in mcp_tools}
    == {
        "audit_direction_binding_tool",
        "audit_requirement_relations_tool",
        "semantic_guard_schema_tool",
        "shadow_compare_legacy_tool",
    },
    "MCP tool surface is not the canonical v1 contract",
)
require(
    {str(resource.uri) for resource in mcp_resources}
    == {"semantic-guard://constitution/v1"},
    "MCP static resource surface is not canonical",
)
require(
    {template.uriTemplate for template in mcp_resource_templates}
    == {"semantic-guard://schemas/{name}"},
    "MCP resource-template surface is not canonical",
)

selected_schema_directory = schema_directory().resolve()
selected_lifecycle = Path(lifecycle_profiles._CANDIDATE_PATH).resolve()
selected_operational = Path(operational_outcomes._SCHEMA_PATH).resolve()
require(
    selected_schema_directory == package_root / "schemas",
    f"schema directory escaped package: {selected_schema_directory}",
)
require(
    selected_lifecycle == package_root / "validation" / "lifecycle-profile-registry.candidate.json",
    f"lifecycle candidate escaped package: {selected_lifecycle}",
)
require(
    selected_operational == package_root / "schemas" / "operational-outcome-evaluation.schema.json",
    f"operational schema escaped package: {selected_operational}",
)

present_names = {
    path.name.removesuffix(".schema.json")
    for path in selected_schema_directory.glob("*.schema.json")
}
known_names = set(KNOWN_SCHEMA_NAMES)
require(len(known_names) == 24, f"expected 24 public schemas, found {len(known_names)}")
require(present_names == known_names, "KNOWN_SCHEMA_NAMES and packaged schemas differ")

loaded = {}
for name in sorted(known_names):
    schema = load_public_schema(name)
    Draft202012Validator.check_schema(schema)
    resource_schema = json.loads(semantic_guard_schema_resource(name))
    require(resource_schema == schema, f"MCP schema resource differs for {name}")
    loaded[name] = schema

parser = build_parser()
subparsers_action = next(
    action for action in parser._actions
    if isinstance(action, argparse._SubParsersAction)
)
schema_parser = subparsers_action.choices["schema"]
canonical_cli_commands = {
    "audit-requirement",
    "audit-direction-binding",
    "shadow-compare",
    "schema",
    "workflow",
    "candidate",
}
require(
    set(subparsers_action.choices) == canonical_cli_commands,
    "canonical CLI surface differs from the four commands plus explicit routes",
)
schema_name_action = next(action for action in schema_parser._actions if action.dest == "name")
require(set(schema_name_action.choices) == known_names, "CLI schema choices differ from public schemas")

try:
    load_public_schema("../common")
except ValueError:
    pass
else:
    raise RuntimeError("public schema loader accepted path selection")

lifecycle_registry = load_candidate_registry()
validate_lifecycle_profile_registry(lifecycle_registry)
require(
    lifecycle_registry.get("schema_version") == "lifecycle-profile-registry/v0",
    "wrong lifecycle candidate was loaded",
)
require(len(lifecycle_registry.get("profiles", [])) == 10, "lifecycle profile denominator is not ten")

package_resources = resources.files("semantic_guard")
engineering_schema_resource = package_resources.joinpath(
    "validation/engineering-rule-pack.schema.json"
)
engineering_candidate_resource = package_resources.joinpath(
    "validation/engineering-rule-pack.candidate.json"
)
require(engineering_schema_resource.is_file(), "engineering rule-pack schema is missing")
require(engineering_candidate_resource.is_file(), "engineering rule-pack candidate is missing")
engineering_schema = json.loads(engineering_schema_resource.read_text(encoding="utf-8"))
engineering_candidate = json.loads(engineering_candidate_resource.read_text(encoding="utf-8"))
Draft202012Validator.check_schema(engineering_schema)
engineering_errors = list(
    Draft202012Validator(
        engineering_schema,
        format_checker=FormatChecker(),
    ).iter_errors(engineering_candidate)
)
require(
    not engineering_errors,
    "engineering rule-pack candidate failed its packaged schema: "
    + "; ".join(error.message for error in engineering_errors[:3]),
)
require(len(engineering_candidate.get("rules", [])) == 11, "engineering rule denominator is not eleven")

operational_schema = load_public_schema("operational-outcome-evaluation")
require(
    not Draft202012Validator(operational_schema).is_valid({}),
    "public operational schema accepted an empty object",
)
require(
    not operational_outcomes._schema_validator().is_valid({}),
    "operational validator selected the permissive adjacent decoy",
)

audit_payload = audit_requirement_relations_service(
    """Purpose: 検索APIが検索結果を返す
User: 検索API
Scenario: 検索APIが検索要求を処理して検索結果を返す
Expected result: 検索結果を返す
Acceptance criteria: 検索結果を返す
Verification method: 検索結果を試験で確認する
Evidence: 検索結果の試験報告""",
    analysis_mode="conditional",
)
producer_records = [
    item
    for item in audit_payload["provenance"]
    if item["source_ref"].get("role") == "audit_producer"
]
require(len(producer_records) == 1, "public audit does not identify exactly one producer")
require(
    producer_records[0]["source_ref"].get("entity_version") == "1.2.0.dev0",
    "public audit producer version is not v1.2.0.dev0",
)
direction_payload = audit_direction_binding_service(
    "横一列で、Aの次の項目はどれですか？",
    recorded_at="2026-08-23T00:00:00Z",
)
require(
    direction_payload["primary_rule_evaluation"]["state"] == "indeterminate",
    "provider-free direction audit did not fail closed",
)
require(
    direction_payload["workflow_disposition"]["status"] == "warn",
    "provider-free direction audit has the wrong workflow disposition",
)
Draft202012Validator(
    loaded["direction-binding-audit"],
    format_checker=FormatChecker(),
).validate(direction_payload)
direction_tool_content, direction_tool_payload = asyncio.run(
    mcp.call_tool(
        "audit_direction_binding_tool",
        {
            "text": "横一列で、Aの次の項目はどれですか？",
            "recorded_at": "2026-08-23T00:00:00Z",
        },
    )
)
require(direction_tool_content, "direction-binding MCP dispatch returned no content")
require(
    direction_tool_payload == direction_payload,
    "direction-binding MCP dispatch differs from the service projection",
)

# All surfaces are imported together in the same fresh environment. Successful
# imports in three separate environments would miss namespace/resource leakage.
from semantic_guard_workflow import cli as workflow_cli
from semantic_guard_workflow import resources as workflow_resources
from semantic_guard_workflow.mcp_server import mcp as workflow_mcp
from semantic_guard_workflow.models import load_audit_result_schema
from semantic_guard_workflow.acceptance_review import load_acceptance_review_bundle_schema
from semantic_guard_workflow.llm_review import load_candidate_gap_review_schema
from semantic_guard_workflow.request_exploration_review import load_request_exploration_review_schema
from semantic_guard_vnext import cli as candidate_cli
from semantic_guard_vnext import schema_access as candidate_schema_access
from semantic_guard_vnext.mcp_server import mcp as candidate_mcp
from semantic_guard_vnext.public_contract import (
    KNOWN_SCHEMA_NAMES as CANDIDATE_SCHEMA_NAMES,
    load_public_schema as load_candidate_schema,
)
from semantic_guard_vnext.candidate_governance_adapters import (
    load_default_engineering_rule_pack_candidate,
    load_default_lifecycle_profile_registry_candidate,
)
import semantic_guard_u10_broker

namespace_roots = {}
for namespace in ("semantic_guard", "semantic_guard_workflow", "semantic_guard_vnext",
                  "semantic_guard_u10_broker"):
    namespace_spec = importlib.util.find_spec(namespace)
    require(namespace_spec is not None and namespace_spec.submodule_search_locations,
            "missing installed namespace: " + namespace)
    root = Path(tuple(namespace_spec.submodule_search_locations)[0]).resolve()
    require(root.parent == package_root.parent, "namespace imported outside the shared wheel: " + namespace)
    namespace_roots[namespace] = root

workflow_root = namespace_roots["semantic_guard_workflow"]
candidate_root = namespace_roots["semantic_guard_vnext"]
require(workflow_resources.resource_path("schemas").resolve() == workflow_root / "_resources" / "schemas",
        "workflow schemas escaped their owned resources")
require(candidate_schema_access.schema_directory().resolve() == candidate_root / "schemas",
        "candidate schemas escaped their owned resources")
for parts in (("schemas", "audit-result.schema.json"),
              ("docs", "conventions", "base-contract.json"),
              ("tests", "fixtures", "plans", "good.expected.json")):
    path = workflow_resources.resource_path(*parts)
    require(path.is_file(), "workflow resource is missing: " + str(parts))
    require(path.resolve().is_relative_to(workflow_root / "_resources"), "workflow resource escaped its namespace")
require(not workflow_resources.resource_path("schemas", "missing.schema.json").exists(),
        "missing workflow resource unexpectedly resolved")
workflow_schemas = {}
for name, loader in (
    ("audit-result", load_audit_result_schema),
    ("acceptance-review-bundle", load_acceptance_review_bundle_schema),
    ("candidate-gap-review", load_candidate_gap_review_schema),
    ("request-exploration-review", load_request_exploration_review_schema),
):
    schema = loader()
    Draft202012Validator.check_schema(schema)
    require(schema == json.loads(workflow_resources.resource_path("schemas", name + ".schema.json").read_text()),
            "workflow schema loader selected another namespace: " + name)
    workflow_schemas[name] = schema

candidate_schemas = {name: load_candidate_schema(name) for name in CANDIDATE_SCHEMA_NAMES}
require(len(candidate_schemas) == 32, "candidate schema denominator is not 32")
require({p.name.removesuffix(".schema.json") for p in (candidate_root / "schemas").glob("*.schema.json")}
        == set(candidate_schemas), "candidate schema resources differ from their closed list")
for schema in candidate_schemas.values():
    Draft202012Validator.check_schema(schema)
h1_document, h1_bytes, _ = load_default_engineering_rule_pack_candidate()
h2_document, h2_bytes, _ = load_default_lifecycle_profile_registry_candidate()
require(h1_bytes == (candidate_root / "validation" / "engineering-rule-pack.candidate.json").read_bytes(),
        "candidate H1 loaded adjacent or canonical material")
require(h2_bytes == (candidate_root / "validation" / "lifecycle-profile-registry.candidate.json").read_bytes(),
        "candidate H2 loaded adjacent or canonical material")
require(len(h1_document["rules"]) == 11 and len(h2_document["profiles"]) == 10,
        "candidate governance material denominators differ")

workflow_tools = asyncio.run(workflow_mcp.list_tools())
candidate_tools = asyncio.run(candidate_mcp.list_tools())
require(workflow_mcp.name == "semantic-guard-workflow", "workflow MCP name differs")
require(candidate_mcp.name == "semantic-guard-vnext", "candidate MCP name differs")
require({tool.name for tool in workflow_tools} == {
    "explore_request_tool", "llm_explore_request_tool", "llm_explore_request_start_tool",
    "llm_exploration_status_tool", "understand_target_tool", "audit_request_tool",
    "audit_decision_state_tool", "audit_artifact_membership_tool", "audit_plan_tool",
    "audit_diff_tool", "finish_check_tool", "audit_conventions_tool", "conventions_catalog_tool",
    "evaluate_fixtures_tool", "trace_report_tool", "audit_result_schema_tool",
    "request_exploration_review_schema_tool", "rule_detector_map_tool", "doctor_tool",
    "llm_review_command_tool", "llm_review_run_tool", "llm_review_start_tool",
    "review_if_needed_start_tool", "llm_review_status_tool", "review_if_needed_tool",
    "acceptance_bundle_template_tool", "validate_acceptance_bundle_tool",
}, "workflow MCP tool surface differs from its 27-tool contract")
require({tool.name for tool in candidate_tools} == {
    "audit_requirement_relations_vnext_tool", "shadow_compare_legacy_vnext_tool",
    "semantic_guard_vnext_schema_tool",
}, "candidate MCP tool surface differs from its three-tool contract")

def cli_payload(module, arguments, expected_status=0):
    previous_argv = sys.argv
    stdout, stderr = io.StringIO(), io.StringIO()
    try:
        sys.argv = [module.__name__, *arguments]
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                result = module.main()
                status = 0 if result is None else result
            except SystemExit as exc:
                status = exc.code
    finally:
        sys.argv = previous_argv
    require(status == expected_status, f"{module.__name__} {arguments[0]} exit status {status}")
    require(not stderr.getvalue(), "CLI wrote unexpected stderr: " + stderr.getvalue()[:500])
    return json.loads(stdout.getvalue())

workflow_schema = cli_payload(workflow_cli, ["audit-result-schema"])
require(workflow_schema == json.loads(workflow_resources.resource_path("schemas", "audit-result.schema.json").read_text()),
        "workflow schema CLI selected another namespace")
for command in ("audit-plan", "finish-check"):
    payload = cli_payload(workflow_cli, [command, "--text", "確認資料は未提出。"])
    Draft202012Validator(workflow_schema).validate(payload)
    require(payload.get("findings"), "workflow missing-evidence probe produced no findings")
membership_payload = cli_payload(workflow_cli, [
    "audit-artifact-membership", "--text", "公開する操作手順。",
    "--artifact-id", "artifact.wheel-probe", "--purpose", "操作を説明する",
    "--audience", "利用者", "--intended-use", "操作方法を確認する",
])
Draft202012Validator(workflow_schema).validate(membership_payload)
require(membership_payload.get("details", {}).get("schema_version") == "artifact-membership-audit/v0",
        "workflow membership CLI did not execute its dedicated audit")
workflow_content, workflow_schema_payload = asyncio.run(workflow_mcp.call_tool("audit_result_schema_tool", {}))
require(workflow_content and workflow_schema_payload == workflow_schema,
        "workflow MCP schema dispatch differs from its CLI")

candidate_payload = cli_payload(candidate_cli, ["audit-requirement", "--text", "検索APIは検索結果を返す。"], 3)
require(candidate_payload.get("schema_version") == "governed-requirement-audit/v1",
        "candidate default output is not governed-v1")
assessment = candidate_payload["assurance_assessment"]
require(assessment["status"] == "unresolved" and assessment["workflow_disposition"] == "block"
        and assessment["formal_verdict_authority"] == "none" and assessment["blocking_unresolved_count"] > 0,
        "candidate default silently gained adopted authority")
require(candidate_payload["profile_observation"]["adoption_resolution"] == "unresolved",
        "candidate profile was implicitly adopted")
Draft202012Validator(candidate_schemas["governed-audit-result"]).validate(candidate_payload)
candidate_content, candidate_schema_payload = asyncio.run(candidate_mcp.call_tool(
    "semantic_guard_vnext_schema_tool", {"name": "governed-audit-result"}))
require(candidate_content and candidate_schema_payload == candidate_schemas["governed-audit-result"],
        "candidate MCP schema dispatch differs from its loader")

print(json.dumps({
    "schema_version": "semantic-guard-installed-contract-audit/v0",
    "status": "pass",
    "counts": {
        "public_schemas": len(loaded),
        "mcp_schema_resources": len(loaded),
        "cli_schema_names": len(schema_name_action.choices),
        "cli_commands": len(subparsers_action.choices),
        "lifecycle_profiles": len(lifecycle_registry["profiles"]),
        "engineering_rules": len(engineering_candidate["rules"]),
        "mcp_tools": len(mcp_tools),
        "mcp_resources": len(mcp_resources),
        "mcp_resource_templates": len(mcp_resource_templates),
        "producer_records": len(producer_records),
        "installed_namespaces": len(namespace_roots),
        "workflow_mcp_tools": len(workflow_tools),
        "workflow_schemas": len(workflow_schemas),
        "candidate_mcp_tools": len(candidate_tools),
        "candidate_schemas": len(candidate_schemas),
        "workflow_cli_invocations": 4,
        "candidate_cli_invocations": 1,
    },
    "checks": [
        "isolated_installed_import",
        "adjacent_decoys_not_selected",
        "public_schema_surface_closed",
        "mcp_schema_resources_match",
        "cli_schema_names_match",
        "canonical_cli_surface",
        "lifecycle_candidate_valid",
        "engineering_rule_pack_valid",
        "operational_empty_object_rejected",
        "canonical_distribution_identity",
        "canonical_mcp_surface",
        "public_audit_producer_version",
        "direction_binding_provider_free_fail_closed",
        "direction_binding_mcp_dispatch",
        "shared_wheel_namespace_isolation",
        "workflow_owned_resources",
        "workflow_plan_finish_membership_cli",
        "workflow_mcp_surface_and_schema_dispatch",
        "candidate_owned_resources",
        "candidate_governance_remains_unadopted",
        "candidate_mcp_surface_and_schema_dispatch",
    ],
    "digests": {
        "workflow_schema_sha256": hashlib.sha256(json.dumps(
            workflow_schema, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")).hexdigest(),
        "candidate_schema_sha256": hashlib.sha256(json.dumps(
            candidate_schemas["governed-audit-result"], ensure_ascii=False,
            sort_keys=True, separators=(",", ":")
        ).encode("utf-8")).hexdigest(),
        "state_assessment_schema_sha256": hashlib.sha256(
            json.dumps(
                loaded["state-assessment"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
        "direction_binding_schema_sha256": hashlib.sha256(
            json.dumps(
                loaded["direction-binding-audit"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
        "direction_binding_payload_sha256": hashlib.sha256(
            json.dumps(
                direction_payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
    },
}, ensure_ascii=False, sort_keys=True))
'''


class VerificationFailure(RuntimeError):
    """Expected verifier failure with a stable machine-readable code."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        phase: str,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.phase = phase
        self.details = dict(details or {})


class JsonArgumentParser(argparse.ArgumentParser):
    """Keep argument failures inside the JSON result contract."""

    def error(self, message: str) -> None:
        raise VerificationFailure(
            "invalid_arguments",
            message,
            phase="arguments",
        )


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str


def _json_print(payload: Mapping[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_json_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _validate_wheel(path_value: str | Path) -> tuple[Path, int, str]:
    path = Path(path_value).expanduser()
    if path.suffix != ".whl":
        raise VerificationFailure(
            "wheel_suffix_invalid",
            "--wheel must name a .whl file",
            phase="wheel_preflight",
        )
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise VerificationFailure(
            "wheel_unavailable",
            f"wheel could not be inspected: {exc}",
            phase="wheel_preflight",
        ) from exc
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
        raise VerificationFailure(
            "wheel_not_regular_file",
            "--wheel must be a non-symlink regular file",
            phase="wheel_preflight",
        )
    if metadata.st_size <= 0 or metadata.st_size > MAX_WHEEL_BYTES:
        raise VerificationFailure(
            "wheel_size_out_of_bounds",
            f"wheel size must be within 1..{MAX_WHEEL_BYTES} bytes",
            phase="wheel_preflight",
            details={"observed_bytes": metadata.st_size},
        )
    resolved = path.resolve(strict=True)
    try:
        with zipfile.ZipFile(resolved) as archive:
            members = archive.infolist()
            if len(members) > MAX_WHEEL_ENTRIES:
                raise VerificationFailure(
                    "wheel_entry_limit_exceeded",
                    f"wheel contains more than {MAX_WHEEL_ENTRIES} entries",
                    phase="wheel_preflight",
                    details={"observed_entries": len(members)},
                )
            total_uncompressed = 0
            observed_resources = set()
            for member in members:
                normalized_name = member.filename.replace("\\", "/")
                parts = PurePosixPath(normalized_name).parts
                unix_mode = member.external_attr >> 16
                if (
                    not parts
                    or PurePosixPath(normalized_name).is_absolute()
                    or ".." in parts
                    or ":" in parts[0]
                    or member.flag_bits & 0x1
                    or stat.S_ISLNK(unix_mode)
                ):
                    raise VerificationFailure(
                        "wheel_member_unsafe",
                        f"unsafe wheel member: {member.filename!r}",
                        phase="wheel_preflight",
                    )
                if member.filename.casefold().endswith(".pth"):
                    raise VerificationFailure(
                        "wheel_pth_not_allowed",
                        f"wheel may not install executable .pth files: {member.filename!r}",
                        phase="wheel_preflight",
                    )
                if _wheel_member_crosses_distribution_boundary(parts):
                    raise VerificationFailure(
                        "wheel_distribution_boundary_violation",
                        f"non-runtime repository material entered the wheel: {member.filename!r}",
                        phase="wheel_preflight",
                    )
                if not member.is_dir():
                    observed_resources.add("/".join(parts))
                total_uncompressed += member.file_size
                if total_uncompressed > MAX_WHEEL_UNCOMPRESSED_BYTES:
                    raise VerificationFailure(
                        "wheel_uncompressed_limit_exceeded",
                        "wheel uncompressed size exceeds the verifier limit",
                        phase="wheel_preflight",
                        details={"observed_bytes": total_uncompressed},
                    )
            missing_resources = _ALLOWED_ADDITIONAL_RESOURCES - observed_resources
            if missing_resources:
                raise VerificationFailure(
                    "wheel_required_resource_missing",
                    "wheel is missing declared workflow or candidate runtime resources",
                    phase="wheel_preflight",
                    details={"missing_resources": sorted(missing_resources)},
                )
    except zipfile.BadZipFile as exc:
        raise VerificationFailure(
            "wheel_zip_invalid",
            "wheel is not a valid ZIP archive",
            phase="wheel_preflight",
        ) from exc
    return resolved, metadata.st_size, _sha256(resolved)


def _wheel_member_crosses_distribution_boundary(parts: tuple[str, ...]) -> bool:
    if not parts:
        return True
    if parts[0] not in _CANONICAL_WHEEL_ROOTS:
        return True
    if "semantic-guard-v0.1.0" in parts:
        return True
    if parts[0] == "semantic_guard-1.2.0.dev0.dist-info":
        if len(parts) == 2:
            return parts[1] not in {"METADATA", "RECORD", "WHEEL", "entry_points.txt"}
        return not (
            len(parts) == 3
            and parts[1] == "licenses"
            and parts[2] == "LICENSE"
        )
    if parts[0] in _RUNTIME_NAMESPACES - {"semantic_guard"}:
        return _additional_namespace_member_forbidden(parts)
    if any(part in {"docs", "legacy", "migration", "tests"} for part in parts[1:]):
        return True
    if len(parts) >= 2 and parts[0] == "semantic_guard" and parts[1] == "validation":
        return len(parts) != 3 or parts[2] not in _ALLOWED_PACKAGED_VALIDATION_FILES
    return False


def _additional_namespace_member_forbidden(parts: tuple[str, ...]) -> bool:
    """Permit code and an exact set of package-owned data, never history."""
    relative = "/".join(parts)
    if relative in _ALLOWED_ADDITIONAL_RESOURCES:
        return False
    if any(name.startswith(relative + "/") for name in _ALLOWED_ADDITIONAL_RESOURCES):
        return False  # archive directory records for the fixed resources
    if len(parts) == 1:
        return False
    if any(part in {"docs", "legacy", "migration", "tests", "__pycache__", "_resources",
                    "schemas", "constitution", "validation"} for part in parts[1:]):
        return True
    return not (parts[-1].endswith(".py") or len(parts) == 2 and parts[-1] in {"audit", "runtime"})


def _validate_sdist(path_value: str | Path | None) -> tuple[Path, int, str]:
    if path_value is None:
        raise VerificationFailure(
            "sdist_required",
            "--sdist is required so repository-only archives and histories are checked",
            phase="sdist_preflight",
        )
    path = Path(path_value).expanduser()
    if not path.name.endswith(".tar.gz"):
        raise VerificationFailure(
            "sdist_suffix_invalid",
            "--sdist must name a .tar.gz file",
            phase="sdist_preflight",
        )
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise VerificationFailure(
            "sdist_unavailable",
            f"sdist could not be inspected: {exc}",
            phase="sdist_preflight",
        ) from exc
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
        raise VerificationFailure(
            "sdist_not_regular_file",
            "--sdist must be a non-symlink regular file",
            phase="sdist_preflight",
        )
    if metadata.st_size <= 0 or metadata.st_size > MAX_SDIST_BYTES:
        raise VerificationFailure(
            "sdist_size_out_of_bounds",
            f"sdist size must be within 1..{MAX_SDIST_BYTES} bytes",
            phase="sdist_preflight",
            details={"observed_bytes": metadata.st_size},
        )
    resolved = path.resolve(strict=True)
    try:
        with tarfile.open(resolved, mode="r:gz") as archive:
            members = archive.getmembers()
            if len(members) > MAX_SDIST_ENTRIES:
                raise VerificationFailure(
                    "sdist_entry_limit_exceeded",
                    f"sdist contains more than {MAX_SDIST_ENTRIES} entries",
                    phase="sdist_preflight",
                    details={"observed_entries": len(members)},
                )
            total_uncompressed = 0
            observed_resources = set()
            for member in members:
                normalized_name = member.name.replace("\\", "/")
                parts = PurePosixPath(normalized_name).parts
                if (
                    not parts
                    or PurePosixPath(normalized_name).is_absolute()
                    or ".." in parts
                    or ":" in parts[0]
                    or parts[0] != _CANONICAL_SDIST_ROOT
                    or member.issym()
                    or member.islnk()
                    or member.isdev()
                    or not (member.isfile() or member.isdir())
                ):
                    raise VerificationFailure(
                        "sdist_member_unsafe",
                        f"unsafe sdist member: {member.name!r}",
                        phase="sdist_preflight",
                    )
                relative = parts[1:]
                if not relative:
                    continue
                if _sdist_member_crosses_distribution_boundary(relative):
                    raise VerificationFailure(
                        "sdist_distribution_boundary_violation",
                        f"repository-only material entered the sdist: {member.name!r}",
                        phase="sdist_preflight",
                    )
                if member.isfile() and relative[0] == "src":
                    observed_resources.add("/".join(relative[1:]))
                total_uncompressed += member.size
                if total_uncompressed > MAX_SDIST_UNCOMPRESSED_BYTES:
                    raise VerificationFailure(
                        "sdist_uncompressed_limit_exceeded",
                        "sdist uncompressed size exceeds the verifier limit",
                        phase="sdist_preflight",
                        details={"observed_bytes": total_uncompressed},
                    )
            missing_resources = _ALLOWED_ADDITIONAL_RESOURCES - observed_resources
            if missing_resources:
                raise VerificationFailure(
                    "sdist_required_resource_missing",
                    "sdist is missing declared workflow or candidate runtime resources",
                    phase="sdist_preflight",
                    details={"missing_resources": sorted(missing_resources)},
                )
    except tarfile.TarError as exc:
        raise VerificationFailure(
            "sdist_tar_invalid",
            "sdist is not a valid gzip-compressed tar archive",
            phase="sdist_preflight",
        ) from exc
    return resolved, metadata.st_size, _sha256(resolved)


def _sdist_member_crosses_distribution_boundary(parts: tuple[str, ...]) -> bool:
    if not parts or parts[0] not in _ALLOWED_SDIST_ROOTS:
        return True
    if parts[0] == "src" and len(parts) >= 2:
        if parts[1] not in _RUNTIME_NAMESPACES:
            return True
        if parts[1] != "semantic_guard":
            return _additional_namespace_member_forbidden(parts[1:])
    if any(part in {"docs", "legacy", "migration", "tests"} for part in parts[1:]):
        return True
    if parts[0] == "validation":
        return len(parts) != 2 or parts[1] not in _ALLOWED_PACKAGED_VALIDATION_FILES
    return False


def _child_limit_function(cpu_seconds: int):
    if os.name != "posix":
        return None

    def apply_limits() -> None:
        import resource

        def set_limit(name: str, desired: int) -> None:
            kind = getattr(resource, name, None)
            if kind is None:
                return
            _soft, hard = resource.getrlimit(kind)
            bounded = desired if hard == resource.RLIM_INFINITY else min(desired, hard)
            resource.setrlimit(kind, (bounded, bounded))

        set_limit("RLIMIT_CPU", cpu_seconds)
        set_limit("RLIMIT_FSIZE", MAX_CHILD_FILE_BYTES)
        # Darwin exposes RLIMIT_AS but rejects finite values in pre-exec
        # children.  Keep the portable input, archive, time, output, file and
        # descriptor bounds there; apply the address-space cap where the
        # platform actually supports it.
        if _address_space_limit_supported():
            set_limit("RLIMIT_AS", MAX_CHILD_ADDRESS_SPACE_BYTES)
        set_limit("RLIMIT_NOFILE", MAX_CHILD_OPEN_FILES)

    return apply_limits


def _address_space_limit_supported() -> bool:
    return os.name == "posix" and sys.platform != "darwin"


def _read_capture(handle: Any, *, stream: str, phase: str) -> str:
    handle.seek(0)
    data = handle.read(MAX_CAPTURE_BYTES + 1)
    if len(data) > MAX_CAPTURE_BYTES:
        raise VerificationFailure(
            "subprocess_output_limit_exceeded",
            f"{phase} {stream} exceeded {MAX_CAPTURE_BYTES} bytes",
            phase=phase,
        )
    return data.decode("utf-8", errors="replace")


def _run_process(
    command: Sequence[str],
    *,
    allowed_executables: frozenset[Path],
    cwd: Path,
    env: Mapping[str, str],
    timeout_seconds: float,
    phase: str,
) -> ProcessResult:
    if not command:
        raise VerificationFailure(
            "empty_command",
            "internal verifier command was empty",
            phase=phase,
        )
    executable = Path(command[0]).absolute()
    executable.resolve(strict=True)
    if executable not in allowed_executables:
        raise VerificationFailure(
            "executable_not_allowed",
            "verifier attempted to select an executable outside its fixed set",
            phase=phase,
        )
    cpu_seconds = max(2, math.ceil(timeout_seconds) + 2)
    popen_options: dict[str, Any] = {
        "cwd": cwd,
        "env": dict(env),
        "stdin": subprocess.DEVNULL,
        "text": False,
    }
    if os.name == "posix":
        popen_options["start_new_session"] = True
        popen_options["preexec_fn"] = _child_limit_function(cpu_seconds)

    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        process = subprocess.Popen(
            list(command),
            stdout=stdout_file,
            stderr=stderr_file,
            **popen_options,
        )
        try:
            returncode = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            process.wait()
            raise VerificationFailure(
                "subprocess_timeout",
                f"{phase} exceeded {timeout_seconds:.1f} seconds",
                phase=phase,
            ) from exc
        stdout = _read_capture(stdout_file, stream="stdout", phase=phase)
        stderr = _read_capture(stderr_file, stream="stderr", phase=phase)
    return ProcessResult(returncode=returncode, stdout=stdout, stderr=stderr)


def _require_success(result: ProcessResult, *, phase: str) -> None:
    if result.returncode == 0:
        return
    raise VerificationFailure(
        "subprocess_failed",
        f"{phase} exited with status {result.returncode}",
        phase=phase,
        details={
            "returncode": result.returncode,
            "stderr": result.stderr[-4096:],
            "stdout": result.stdout[-4096:],
        },
    )


def _remaining(deadline: float, *, phase: str) -> float:
    value = deadline - time.monotonic()
    if value <= 0:
        raise VerificationFailure(
            "verification_timeout",
            "the packaged-contract verification deadline expired",
            phase=phase,
        )
    return value


def _venv_python(venv_root: Path) -> Path:
    if os.name == "nt":
        return venv_root / "Scripts" / "python.exe"
    return venv_root / "bin" / "python"


def _venv_console_script(venv_root: Path, name: str) -> Path:
    if os.name == "nt":
        return venv_root / "Scripts" / f"{name}.exe"
    return venv_root / "bin" / name


def _clean_environment(*, home: Path, temporary: Path, executable_directory: Path) -> dict[str, str]:
    environment = {
        "HOME": str(home),
        "PATH": str(executable_directory) + os.pathsep + os.defpath,
        "PIP_CONFIG_FILE": os.devnull,
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_NO_INPUT": "1",
        "PYTHONHASHSEED": "0",
        "PYTHONNOUSERSITE": "1",
        "TMPDIR": str(temporary),
    }
    for name in (
        "ALL_PROXY",
        "HTTPS_PROXY",
        "HTTP_PROXY",
        "NO_PROXY",
        "SSL_CERT_FILE",
        "REQUESTS_CA_BUNDLE",
    ):
        value = os.environ.get(name)
        if value:
            environment[name] = value
    return environment


def verify_wheel(
    wheel_value: str | Path,
    *,
    sdist_value: str | Path | None = None,
    timeout_seconds: float,
) -> dict[str, Any]:
    if not MIN_TIMEOUT_SECONDS <= timeout_seconds <= MAX_TIMEOUT_SECONDS:
        raise VerificationFailure(
            "timeout_out_of_bounds",
            f"timeout must be between {MIN_TIMEOUT_SECONDS:g} and {MAX_TIMEOUT_SECONDS:g} seconds",
            phase="arguments",
        )
    wheel, wheel_bytes, wheel_digest = _validate_wheel(wheel_value)
    sdist, sdist_bytes, sdist_digest = _validate_sdist(sdist_value)
    deadline = time.monotonic() + timeout_seconds

    with tempfile.TemporaryDirectory(prefix="semantic-guard-wheel-") as directory:
        root = Path(directory).resolve()
        home = root / "home"
        temporary = root / "tmp"
        venv_root = root / "venv"
        home.mkdir()
        temporary.mkdir()

        bootstrap_environment = _clean_environment(
            home=home,
            temporary=temporary,
            executable_directory=Path(sys.executable).resolve().parent,
        )
        host_python = Path(sys.executable).absolute()
        host_python.resolve(strict=True)
        create_result = _run_process(
            [str(host_python), "-I", "-m", "venv", str(venv_root)],
            allowed_executables=frozenset({host_python}),
            cwd=root,
            env=bootstrap_environment,
            timeout_seconds=_remaining(deadline, phase="create_venv"),
            phase="create_venv",
        )
        _require_success(create_result, phase="create_venv")

        installed_python = _venv_python(venv_root).absolute()
        installed_python.resolve(strict=True)
        installed_environment = _clean_environment(
            home=home,
            temporary=temporary,
            executable_directory=installed_python.parent,
        )
        install_result = _run_process(
            [
                str(installed_python),
                "-I",
                "-m",
                "pip",
                "install",
                "--isolated",
                "--require-virtualenv",
                "--only-binary=:all:",
                "--no-input",
                "--no-compile",
                str(wheel),
            ],
            allowed_executables=frozenset({installed_python}),
            cwd=root,
            env=installed_environment,
            timeout_seconds=_remaining(deadline, phase="install_wheel"),
            phase="install_wheel",
        )
        _require_success(install_result, phase="install_wheel")

        audit_result = _run_process(
            [str(installed_python), "-I", "-c", _AUDIT_PROGRAM],
            allowed_executables=frozenset({installed_python}),
            cwd=root,
            env=installed_environment,
            timeout_seconds=_remaining(deadline, phase="audit_installed_wheel"),
            phase="audit_installed_wheel",
        )
        _require_success(audit_result, phase="audit_installed_wheel")
        try:
            installed_audit = json.loads(audit_result.stdout)
        except json.JSONDecodeError as exc:
            raise VerificationFailure(
                "installed_audit_output_invalid",
                "installed audit did not return exactly one JSON value",
                phase="audit_installed_wheel",
                details={"stdout": audit_result.stdout[-4096:]},
            ) from exc
        if not isinstance(installed_audit, dict) or installed_audit.get("status") != "pass":
            raise VerificationFailure(
                "installed_audit_not_passed",
                "installed audit did not report pass",
                phase="audit_installed_wheel",
                details={"audit": installed_audit},
            )

        console_script = _venv_console_script(
            venv_root,
            "semantic-guard",
        ).absolute()
        try:
            console_metadata = console_script.lstat()
        except OSError as exc:
            raise VerificationFailure(
                "console_entrypoint_missing",
                f"installed console entrypoint is unavailable: {exc}",
                phase="audit_console_entrypoint",
            ) from exc
        if not stat.S_ISREG(console_metadata.st_mode) or console_script.is_symlink():
            raise VerificationFailure(
                "console_entrypoint_not_regular",
                "installed console entrypoint must be a non-symlink regular file",
                phase="audit_console_entrypoint",
            )
        mcp_console_script = _venv_console_script(
            venv_root,
            "semantic-guard-mcp",
        ).absolute()
        try:
            mcp_console_metadata = mcp_console_script.lstat()
        except OSError as exc:
            raise VerificationFailure(
                "mcp_console_entrypoint_missing",
                f"installed MCP console entrypoint is unavailable: {exc}",
                phase="audit_console_entrypoint",
            ) from exc
        if (
            not stat.S_ISREG(mcp_console_metadata.st_mode)
            or mcp_console_script.is_symlink()
        ):
            raise VerificationFailure(
                "mcp_console_entrypoint_not_regular",
                "installed MCP console entrypoint must be a non-symlink regular file",
                phase="audit_console_entrypoint",
            )
        version_result = _run_process(
            [str(console_script), "--version"],
            allowed_executables=frozenset({console_script}),
            cwd=root,
            env=installed_environment,
            timeout_seconds=_remaining(deadline, phase="audit_console_version"),
            phase="audit_console_version",
        )
        _require_success(version_result, phase="audit_console_version")
        if version_result.stdout != "semantic-guard 1.2.0.dev0\n" or version_result.stderr:
            raise VerificationFailure(
                "console_version_mismatch",
                "installed console version does not identify semantic-guard 1.2.0.dev0",
                phase="audit_console_version",
                details={
                    "stdout": version_result.stdout[-4096:],
                    "stderr": version_result.stderr[-4096:],
                },
            )
        console_result = _run_process(
            [str(console_script), "schema", "state-assessment"],
            allowed_executables=frozenset({console_script}),
            cwd=root,
            env=installed_environment,
            timeout_seconds=_remaining(deadline, phase="audit_console_entrypoint"),
            phase="audit_console_entrypoint",
        )
        _require_success(console_result, phase="audit_console_entrypoint")
        if console_result.stderr:
            raise VerificationFailure(
                "console_entrypoint_stderr_not_empty",
                "installed schema command wrote unexpected standard error",
                phase="audit_console_entrypoint",
                details={"stderr": console_result.stderr[-4096:]},
            )
        try:
            console_schema = json.loads(console_result.stdout)
        except json.JSONDecodeError as exc:
            raise VerificationFailure(
                "console_entrypoint_output_invalid",
                "installed schema command did not return exactly one JSON value",
                phase="audit_console_entrypoint",
                details={"stdout": console_result.stdout[-4096:]},
            ) from exc
        expected_schema_digest = (
            installed_audit.get("digests", {}).get(
                "state_assessment_schema_sha256"
            )
        )
        if (
            not isinstance(expected_schema_digest, str)
            or _canonical_json_sha256(console_schema) != expected_schema_digest
        ):
            raise VerificationFailure(
                "console_entrypoint_schema_mismatch",
                "installed console schema differs from load_public_schema",
                phase="audit_console_entrypoint",
            )

        direction_schema_result = _run_process(
            [str(console_script), "schema", "direction-binding-audit"],
            allowed_executables=frozenset({console_script}),
            cwd=root,
            env=installed_environment,
            timeout_seconds=_remaining(
                deadline,
                phase="audit_direction_schema_entrypoint",
            ),
            phase="audit_direction_schema_entrypoint",
        )
        _require_success(
            direction_schema_result,
            phase="audit_direction_schema_entrypoint",
        )
        if direction_schema_result.stderr:
            raise VerificationFailure(
                "direction_schema_entrypoint_stderr_not_empty",
                "installed direction schema command wrote unexpected standard error",
                phase="audit_direction_schema_entrypoint",
                details={"stderr": direction_schema_result.stderr[-4096:]},
            )
        try:
            direction_schema = json.loads(direction_schema_result.stdout)
        except json.JSONDecodeError as exc:
            raise VerificationFailure(
                "direction_schema_entrypoint_output_invalid",
                "installed direction schema command did not return one JSON value",
                phase="audit_direction_schema_entrypoint",
            ) from exc
        expected_direction_schema_digest = installed_audit.get("digests", {}).get(
            "direction_binding_schema_sha256"
        )
        if (
            not isinstance(expected_direction_schema_digest, str)
            or _canonical_json_sha256(direction_schema)
            != expected_direction_schema_digest
        ):
            raise VerificationFailure(
                "direction_schema_entrypoint_mismatch",
                "installed direction schema differs from load_public_schema",
                phase="audit_direction_schema_entrypoint",
            )

        direction_command = [
            str(console_script),
            "audit-direction-binding",
            "--text",
            "横一列で、Aの次の項目はどれですか？",
            "--recorded-at",
            "2026-08-23T00:00:00Z",
        ]
        direction_result = _run_process(
            direction_command,
            allowed_executables=frozenset({console_script}),
            cwd=root,
            env=installed_environment,
            timeout_seconds=_remaining(
                deadline,
                phase="audit_direction_console_entrypoint",
            ),
            phase="audit_direction_console_entrypoint",
        )
        _require_success(direction_result, phase="audit_direction_console_entrypoint")
        if direction_result.stderr:
            raise VerificationFailure(
                "direction_console_entrypoint_stderr_not_empty",
                "installed direction audit wrote unexpected standard error",
                phase="audit_direction_console_entrypoint",
                details={"stderr": direction_result.stderr[-4096:]},
            )
        try:
            direction_payload = json.loads(direction_result.stdout)
        except json.JSONDecodeError as exc:
            raise VerificationFailure(
                "direction_console_entrypoint_output_invalid",
                "installed direction audit did not return one JSON value",
                phase="audit_direction_console_entrypoint",
            ) from exc
        expected_direction_payload_digest = installed_audit.get("digests", {}).get(
            "direction_binding_payload_sha256"
        )
        if (
            not isinstance(expected_direction_payload_digest, str)
            or _canonical_json_sha256(direction_payload)
            != expected_direction_payload_digest
        ):
            raise VerificationFailure(
                "direction_console_entrypoint_mismatch",
                "installed direction audit differs from MCP/service projection",
                phase="audit_direction_console_entrypoint",
            )

        fail_on_result = _run_process(
            [*direction_command, "--fail-on", "warn"],
            allowed_executables=frozenset({console_script}),
            cwd=root,
            env=installed_environment,
            timeout_seconds=_remaining(
                deadline,
                phase="audit_direction_console_fail_on",
            ),
            phase="audit_direction_console_fail_on",
        )
        if (
            fail_on_result.returncode != 3
            or fail_on_result.stderr
            or _canonical_json_sha256(json.loads(fail_on_result.stdout))
            != expected_direction_payload_digest
        ):
            raise VerificationFailure(
                "direction_console_fail_on_mismatch",
                "installed --fail-on changed payload or did not return status 3",
                phase="audit_direction_console_fail_on",
                details={
                    "returncode": fail_on_result.returncode,
                    "stderr": fail_on_result.stderr[-4096:],
                },
            )

        extra_consoles = {}
        for name in sorted(_CONSOLE_ENTRYPOINTS - {"semantic-guard", "semantic-guard-mcp"}):
            entrypoint = _venv_console_script(venv_root, name).absolute()
            try:
                metadata = entrypoint.lstat()
            except OSError as exc:
                raise VerificationFailure(
                    "console_entrypoint_missing", f"missing {name}: {exc}",
                    phase="audit_added_console_entrypoints",
                ) from exc
            if not stat.S_ISREG(metadata.st_mode) or entrypoint.is_symlink():
                raise VerificationFailure(
                    "console_entrypoint_not_regular", f"non-regular {name}",
                    phase="audit_added_console_entrypoints",
                )
            extra_consoles[name] = entrypoint

        added_cases = (
            ("semantic-guard-workflow", ["audit-result-schema"], 0, "workflow_schema"),
            ("semantic-guard-workflow", ["audit-plan", "--text", "確認資料は未提出。"], 0, "workflow_audit"),
            ("semantic-guard-workflow", ["finish-check", "--text", "確認資料は未提出。"], 0, "workflow_audit"),
            ("semantic-guard-workflow", ["audit-artifact-membership", "--text", "公開する操作手順。",
              "--artifact-id", "artifact.wheel-probe", "--purpose", "操作を説明する",
              "--audience", "利用者", "--intended-use", "操作方法を確認する"], 0, "workflow_membership"),
            ("semantic-guard-vnext", ["schema", "governed-audit-result"], 0, "candidate_schema"),
            ("semantic-guard", ["workflow", "audit-result-schema"], 0, "workflow_schema"),
            ("semantic-guard", ["candidate", "schema", "governed-audit-result"], 0, "candidate_schema"),
        )
        for name, arguments, expected_status, kind in added_cases:
            executable = console_script if name == "semantic-guard" else extra_consoles[name]
            result = _run_process(
                [str(executable), *arguments],
                allowed_executables=frozenset({executable}), cwd=root, env=installed_environment,
                timeout_seconds=_remaining(deadline, phase="audit_added_console_entrypoints"),
                phase="audit_added_console_entrypoints",
            )
            if result.returncode != expected_status or result.stderr:
                raise VerificationFailure(
                    "added_console_behavior_mismatch", f"{name} {arguments[0]} status/stderr mismatch",
                    phase="audit_added_console_entrypoints",
                    details={"returncode": result.returncode, "stderr": result.stderr[-4096:]},
                )
            try:
                payload = json.loads(result.stdout)
            except json.JSONDecodeError as exc:
                raise VerificationFailure(
                    "added_console_output_invalid", f"{name} did not emit one JSON value",
                    phase="audit_added_console_entrypoints",
                ) from exc
            if kind.endswith("_schema"):
                valid = _canonical_json_sha256(payload) == installed_audit["digests"][kind + "_sha256"]
            elif kind == "workflow_membership":
                valid = payload.get("details", {}).get("schema_version") == "artifact-membership-audit/v0"
            else:
                valid = bool(payload.get("findings")) and payload.get("phase") in {"audit_plan", "finish_check"}
            if not valid:
                raise VerificationFailure(
                    "added_console_contract_mismatch", f"{name} {arguments[0]} changed its result contract",
                    phase="audit_added_console_entrypoints",
                )

    checks = [
        *installed_audit["checks"],
        "installed_cli_version_match",
        "installed_cli_schema_match",
        "installed_direction_schema_match",
        "installed_direction_cli_projection_match",
        "installed_direction_cli_fail_on_match",
        "installed_mcp_console_entrypoint_present",
        "six_console_entrypoints_present",
        "installed_workflow_cli_contracts",
        "installed_candidate_cli_unadopted",
        "explicit_canonical_delegation_routes",
    ]
    counts = {
        **installed_audit["counts"],
        "console_entrypoints": len(_CONSOLE_ENTRYPOINTS),
        "console_entrypoint_schemas": 2,
        "direction_cli_invocations": 2,
        "additional_console_invocations": len(added_cases),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "pass",
        "subject": {
            "wheel": str(wheel),
            "sha256": wheel_digest,
            "size_bytes": wheel_bytes,
            "sdist": str(sdist),
            "sdist_sha256": sdist_digest,
            "sdist_size_bytes": sdist_bytes,
        },
        "execution": {
            "timeout_seconds": timeout_seconds,
            "isolated_environment": True,
            "fixed_executables_only": True,
            "subprocess_output_limit_bytes": MAX_CAPTURE_BYTES,
            "wheel_size_limit_bytes": MAX_WHEEL_BYTES,
            "wheel_uncompressed_limit_bytes": MAX_WHEEL_UNCOMPRESSED_BYTES,
            "sdist_size_limit_bytes": MAX_SDIST_BYTES,
            "sdist_uncompressed_limit_bytes": MAX_SDIST_UNCOMPRESSED_BYTES,
            "child_file_limit_bytes": MAX_CHILD_FILE_BYTES,
            "child_address_space_limit_bytes": (
                MAX_CHILD_ADDRESS_SPACE_BYTES
                if _address_space_limit_supported()
                else None
            ),
            "child_open_file_limit": MAX_CHILD_OPEN_FILES,
        },
        "checks": checks,
        "counts": counts,
        "errors": [],
        "limitations": [
            "The supplied wheel is imported inside a temporary virtual environment; this is not an operating-system sandbox for untrusted code.",
            "Use only a trusted local build; a wheel is executable package code even when its resource paths and subprocesses are constrained by this verifier.",
            "Dependency resolution is limited to binary distributions but still depends on the configured package index, network, and current compatible dependency versions.",
            *(
                [
                    "Darwin does not accept a finite RLIMIT_AS for these child processes; wheel size, uncompressed size, wall time, CPU, output, child-file size, and open-file limits remain enforced there."
                ]
                if not _address_space_limit_supported()
                else []
            ),
            "Pass establishes packaged-resource accessibility and local contract replay only; it does not establish field validity, operational qualification, external authenticity, security certification, or human acceptance.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(description=__doc__)
    parser.add_argument("--wheel", required=True, help="Local semantic-guard .whl file.")
    parser.add_argument(
        "--sdist",
        required=True,
        help="Matching local semantic-guard .tar.gz source distribution.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=(
            f"Whole-run wall timeout; {MIN_TIMEOUT_SECONDS:g}..{MAX_TIMEOUT_SECONDS:g} "
            f"seconds (default {DEFAULT_TIMEOUT_SECONDS:g})."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = build_parser().parse_args(argv)
        payload = verify_wheel(
            arguments.wheel,
            sdist_value=arguments.sdist,
            timeout_seconds=arguments.timeout_seconds,
        )
    except VerificationFailure as exc:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "status": "error",
            "subject": None,
            "execution": None,
            "checks": [],
            "counts": {},
            "errors": [
                {
                    "code": exc.code,
                    "phase": exc.phase,
                    "message": str(exc),
                    "details": exc.details,
                }
            ],
            "limitations": [
                "No packaged-contract conclusion may be inferred from an error result."
            ],
        }
        _json_print(payload)
        return 1
    except Exception as exc:  # preserve a JSON failure envelope for unexpected faults
        payload = {
            "schema_version": SCHEMA_VERSION,
            "status": "error",
            "subject": None,
            "execution": None,
            "checks": [],
            "counts": {},
            "errors": [
                {
                    "code": "unexpected_verifier_error",
                    "phase": "verifier",
                    "message": f"{type(exc).__name__}: {exc}",
                    "details": {},
                }
            ],
            "limitations": [
                "No packaged-contract conclusion may be inferred from an error result."
            ],
        }
        _json_print(payload)
        return 1
    _json_print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
