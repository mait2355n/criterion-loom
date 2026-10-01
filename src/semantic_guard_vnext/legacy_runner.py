from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any

from jsonschema import Draft202012Validator


MAX_REQUIREMENT_INPUT_BYTES = 262_144
_BASELINE_SCHEMA_VERSION = "semantic-guard-legacy-baseline/v1"
_BASELINE_PIN_PROFILE = "semantic-guard-requirement-relations-legacy/v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_LEGACY_BASELINE_PATHS = frozenset(
    {
        "docs/prototypes/origin-requirement.md",
        "docs/prototypes/requirement-relation-audit-charter-2026-07-12.md",
        "src/semantic_guard/semantic_assertions.py",
        "src/semantic_guard/requirement_relations.py",
        "src/semantic_guard/request_audit.py",
        "src/semantic_guard/result_builder.py",
        "pyproject.toml",
        "uv.lock",
        ".github/workflows/ci.yml",
        "vnext/scripts/legacy_request_adapter.py",
    }
)
_IGNORED_COVERAGE_PARTS = frozenset({"__pycache__", ".pytest_cache"})


@dataclass(frozen=True, slots=True)
class BaselineCheck:
    status: str
    checked_files: int
    mismatches: tuple[dict[str, str], ...]
    manifest_sha256: str = ""
    pin_profile: str = ""
    runtime_interpreter_path: str = ""
    runtime_python_version: str = ""


@dataclass(frozen=True, slots=True)
class LegacyExecution:
    status: str
    command: tuple[str, ...]
    exit_code: int | None
    stdout_valid_json: bool
    stderr: str
    baseline: BaselineCheck
    result_schema_valid: bool = False
    adapter_pin_status: str = "unchecked"
    invocation_fingerprint: dict[str, Any] = field(default_factory=dict)
    stdout_sha256: str = ""
    stdout_bytes: int = 0


@dataclass(frozen=True, slots=True)
class LegacyObservation:
    schema_version: str
    execution: LegacyExecution
    raw_legacy_result: dict[str, Any] | None
    normalized_legacy_observation: dict[str, Any] | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_requirement_input_size(text: str) -> None:
    """Reject unexpectedly large public inputs before expensive analysis.

    The first vertical slice accepts one structured functional requirement,
    not an arbitrary document corpus.  UTF-8 bytes are counted because that
    is the ingress size seen by CLI and MCP transports.
    """

    size = len(text.encode("utf-8"))
    if size > MAX_REQUIREMENT_INPUT_BYTES:
        raise ValueError(
            "requirement input exceeds "
            f"{MAX_REQUIREMENT_INPUT_BYTES} UTF-8 bytes (received {size})"
        )


def _invalid_manifest(
    baseline_manifest: Path,
    reason: str,
    *,
    path: str = "",
) -> BaselineCheck:
    return BaselineCheck(
        status="invalid_manifest",
        checked_files=0,
        mismatches=(
            {
                "path": path or str(baseline_manifest),
                "reason": reason,
            },
        ),
    )


def _validated_digest_entries(
    manifest: object,
    baseline_manifest: Path,
) -> tuple[
    tuple[tuple[str, str], ...],
    tuple[tuple[str, tuple[str, ...]], ...],
    tuple[str, ...],
    tuple[str, str, str],
] | BaselineCheck:
    if not isinstance(manifest, dict):
        return _invalid_manifest(baseline_manifest, "manifest root must be an object")
    if manifest.get("schema_version") != _BASELINE_SCHEMA_VERSION:
        return _invalid_manifest(
            baseline_manifest,
            f"schema_version must be {_BASELINE_SCHEMA_VERSION}",
        )
    if manifest.get("pin_profile") != _BASELINE_PIN_PROFILE:
        return _invalid_manifest(
            baseline_manifest,
            f"pin_profile must be {_BASELINE_PIN_PROFILE}",
        )
    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict):
        return _invalid_manifest(baseline_manifest, "runtime must be an object")
    interpreter_path = runtime.get("interpreter_path")
    interpreter_sha256 = runtime.get("sha256")
    python_version = runtime.get("python_version")
    if interpreter_path != ".venv/bin/python":
        return _invalid_manifest(
            baseline_manifest,
            "runtime.interpreter_path must be .venv/bin/python",
        )
    if not isinstance(interpreter_sha256, str) or _SHA256.fullmatch(interpreter_sha256) is None:
        return _invalid_manifest(
            baseline_manifest,
            "runtime.sha256 must be 64 lowercase hexadecimal characters",
        )
    if not isinstance(python_version, str) or not python_version.strip():
        return _invalid_manifest(
            baseline_manifest,
            "runtime.python_version must be a non-empty string",
        )
    coverage = manifest.get("coverage")
    if not isinstance(coverage, dict):
        return _invalid_manifest(baseline_manifest, "coverage must be an object")
    raw_scopes = coverage.get("scopes")
    raw_exact_paths = coverage.get("exact_paths")
    if not isinstance(raw_scopes, list) or not raw_scopes:
        return _invalid_manifest(
            baseline_manifest,
            "coverage.scopes must be a non-empty array",
        )
    if not isinstance(raw_exact_paths, list) or not raw_exact_paths:
        return _invalid_manifest(
            baseline_manifest,
            "coverage.exact_paths must be a non-empty array",
        )

    scopes: list[tuple[str, tuple[str, ...]]] = []
    seen_scope_roots: set[str] = set()
    for index, item in enumerate(raw_scopes):
        item_path = f"coverage.scopes[{index}]"
        if not isinstance(item, dict):
            return _invalid_manifest(
                baseline_manifest,
                "coverage scope must be an object",
                path=item_path,
            )
        root = item.get("root")
        suffixes = item.get("suffixes")
        if not isinstance(root, str) or not _is_canonical_relative_path(root):
            return _invalid_manifest(
                baseline_manifest,
                "coverage root must be a canonical relative POSIX path",
                path=item_path,
            )
        if root in seen_scope_roots:
            return _invalid_manifest(
                baseline_manifest,
                "coverage root must be unique",
                path=root,
            )
        if (
            not isinstance(suffixes, list)
            or not suffixes
            or any(
                not isinstance(suffix, str)
                or not suffix.startswith(".")
                or "/" in suffix
                or "\\" in suffix
                for suffix in suffixes
            )
            or len(set(suffixes)) != len(suffixes)
        ):
            return _invalid_manifest(
                baseline_manifest,
                "coverage suffixes must be unique file suffix strings",
                path=item_path,
            )
        seen_scope_roots.add(root)
        scopes.append((root, tuple(suffixes)))

    exact_paths: list[str] = []
    for index, relative in enumerate(raw_exact_paths):
        if not isinstance(relative, str) or not _is_canonical_relative_path(relative):
            return _invalid_manifest(
                baseline_manifest,
                "coverage exact path must be a canonical relative POSIX path",
                path=f"coverage.exact_paths[{index}]",
            )
        if relative in exact_paths:
            return _invalid_manifest(
                baseline_manifest,
                "coverage exact path must be unique",
                path=relative,
            )
        exact_paths.append(relative)
    source_digests = manifest.get("source_digests")
    if not isinstance(source_digests, list) or not source_digests:
        return _invalid_manifest(
            baseline_manifest,
            "source_digests must be a non-empty array",
        )

    entries: list[tuple[str, str]] = []
    seen_paths: set[str] = set()
    for index, item in enumerate(source_digests):
        item_path = f"source_digests[{index}]"
        if not isinstance(item, dict):
            return _invalid_manifest(
                baseline_manifest,
                "digest entry must be an object",
                path=item_path,
            )
        relative = item.get("path")
        expected = item.get("sha256")
        if not isinstance(relative, str) or not relative.strip():
            return _invalid_manifest(
                baseline_manifest,
                "digest path must be a non-empty string",
                path=item_path,
            )
        if not _is_canonical_relative_path(relative):
            return _invalid_manifest(
                baseline_manifest,
                "digest path must be a canonical relative POSIX path",
                path=relative,
            )
        if relative in seen_paths:
            return _invalid_manifest(
                baseline_manifest,
                "digest path must be unique",
                path=relative,
            )
        if not isinstance(expected, str) or _SHA256.fullmatch(expected) is None:
            return _invalid_manifest(
                baseline_manifest,
                "sha256 must be 64 lowercase hexadecimal characters",
                path=relative,
            )
        seen_paths.add(relative)
        entries.append((relative, expected))
    missing_required = REQUIRED_LEGACY_BASELINE_PATHS - seen_paths
    if missing_required:
        return _invalid_manifest(
            baseline_manifest,
            "required pinned paths are missing: " + ", ".join(sorted(missing_required)),
        )
    return (
        tuple(entries),
        tuple(scopes),
        tuple(exact_paths),
        (interpreter_path, interpreter_sha256, python_version),
    )


def _is_canonical_relative_path(value: str) -> bool:
    logical_path = PurePosixPath(value)
    return not (
        logical_path.is_absolute()
        or not logical_path.parts
        or ".." in logical_path.parts
        or "\\" in value
        or logical_path.as_posix() != value
    )


def _covered_paths(
    legacy_root: Path,
    scopes: tuple[tuple[str, tuple[str, ...]], ...],
    exact_paths: tuple[str, ...],
) -> tuple[set[str], list[dict[str, str]]]:
    resolved_root = legacy_root.resolve()
    covered = set(exact_paths)
    problems: list[dict[str, str]] = []
    for relative_root, suffixes in scopes:
        scope_root = (resolved_root / relative_root).resolve()
        try:
            scope_root.relative_to(resolved_root)
        except ValueError:
            problems.append(
                {"path": relative_root, "reason": "coverage_scope_outside_legacy_root"}
            )
            continue
        if not scope_root.is_dir():
            problems.append({"path": relative_root, "reason": "coverage_scope_missing"})
            continue
        for candidate in scope_root.rglob("*"):
            if not candidate.is_file():
                continue
            relative = candidate.relative_to(resolved_root)
            if any(part in _IGNORED_COVERAGE_PARTS for part in relative.parts):
                continue
            if candidate.suffix in suffixes:
                covered.add(relative.as_posix())
    return covered, problems


def check_baseline(legacy_root: Path, baseline_manifest: Path) -> BaselineCheck:
    try:
        manifest = json.loads(baseline_manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return _invalid_manifest(baseline_manifest, str(exc))

    validated = _validated_digest_entries(manifest, baseline_manifest)
    if isinstance(validated, BaselineCheck):
        return validated
    entries, scopes, exact_paths, runtime = validated

    mismatches: list[dict[str, str]] = []
    checked = 0
    resolved_root = legacy_root.resolve()
    interpreter_path, interpreter_expected, python_version = runtime
    covered_paths, coverage_problems = _covered_paths(
        resolved_root,
        scopes,
        exact_paths,
    )
    mismatches.extend(coverage_problems)
    pinned_paths = {relative for relative, _expected in entries}
    for relative in sorted(covered_paths - pinned_paths):
        mismatches.append({"path": relative, "reason": "untracked_in_covered_scope"})
    for relative in sorted(pinned_paths - covered_paths):
        mismatches.append({"path": relative, "reason": "pinned_outside_covered_scope"})
    for relative, expected in entries:
        candidate = (resolved_root / relative).resolve()
        try:
            candidate.relative_to(resolved_root)
        except ValueError:
            return _invalid_manifest(
                baseline_manifest,
                "digest path resolves outside legacy root",
                path=relative,
            )
        if not candidate.is_file():
            mismatches.append({"path": relative, "reason": "missing"})
            continue
        actual = _sha256(candidate)
        checked += 1
        if actual != expected:
            mismatches.append(
                {
                    "path": relative,
                    "reason": "sha256_mismatch",
                    "expected": expected,
                    "actual": actual,
                }
            )
    interpreter = resolved_root / interpreter_path
    if not interpreter.is_file():
        mismatches.append({"path": interpreter_path, "reason": "runtime_missing"})
    else:
        actual = _sha256(interpreter)
        checked += 1
        if actual != interpreter_expected:
            mismatches.append(
                {
                    "path": interpreter_path,
                    "reason": "runtime_sha256_mismatch",
                    "expected": interpreter_expected,
                    "actual": actual,
                }
            )
    return BaselineCheck(
        status="matched" if not mismatches else "drifted",
        checked_files=checked,
        mismatches=tuple(mismatches),
        manifest_sha256=_sha256(baseline_manifest),
        pin_profile=_BASELINE_PIN_PROFILE,
        runtime_interpreter_path=interpreter_path,
        runtime_python_version=python_version,
    )


def _pinned_paths(baseline_manifest: Path) -> set[str]:
    manifest = json.loads(baseline_manifest.read_text(encoding="utf-8"))
    validated = _validated_digest_entries(manifest, baseline_manifest)
    if isinstance(validated, BaselineCheck):
        return set()
    entries, _scopes, _exact_paths, _runtime = validated
    return {relative for relative, _digest in entries}


def _validate_legacy_result(
    legacy_root: Path,
    raw: dict[str, Any] | None,
) -> tuple[bool, str]:
    if raw is None:
        return False, "legacy stdout was not one JSON object"
    schema_path = legacy_root / "schemas" / "audit-result.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        errors = sorted(
            Draft202012Validator(schema).iter_errors(raw),
            key=lambda error: tuple(str(part) for part in error.absolute_path),
        )
    except (OSError, ValueError) as exc:
        return False, f"legacy result schema could not be loaded: {exc}"
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.absolute_path) or "<root>"
        return False, f"legacy result schema violation at {location}: {first.message}"
    if raw.get("phase") != "audit_request":
        return False, "legacy result phase must be audit_request"
    return True, ""


def _normalized_legacy_environment() -> dict[str, str]:
    allowed = {
        key: os.environ[key]
        for key in ("PATH", "SYSTEMROOT", "TMPDIR")
        if key in os.environ
    }
    allowed.update(
        {
            "LC_ALL": "C",
            "PYTHONHASHSEED": "0",
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUTF8": "1",
        }
    )
    return allowed


def run_legacy_request(
    *,
    text: str,
    context: str = "",
    strict: bool = True,
    profile: str = "default",
    logical_trace: str = "summary",
    legacy_root: Path,
    baseline_manifest: Path,
    adapter_script: Path,
    timeout_seconds: float = 30.0,
    allow_baseline_drift: bool = False,
) -> LegacyObservation:
    baseline = check_baseline(legacy_root, baseline_manifest)
    resolved_root = legacy_root.resolve()
    python = resolved_root / (
        baseline.runtime_interpreter_path or ".venv/bin/python"
    )
    try:
        resolved_adapter = adapter_script.resolve(strict=True)
        adapter_relative = resolved_adapter.relative_to(resolved_root).as_posix()
    except (OSError, ValueError):
        resolved_adapter = adapter_script
        adapter_relative = ""
    command = (str(python), str(resolved_adapter))
    if baseline.status == "invalid_manifest":
        return LegacyObservation(
            schema_version="semantic-guard-legacy-observation/v0",
            execution=LegacyExecution(
                status="baseline_invalid",
                command=command,
                exit_code=None,
                stdout_valid_json=False,
                stderr="legacy baseline manifest is invalid; execution was not attempted",
                baseline=baseline,
            ),
            raw_legacy_result=None,
            normalized_legacy_observation=None,
        )
    if baseline.status == "drifted" and not allow_baseline_drift:
        return LegacyObservation(
            schema_version="semantic-guard-legacy-observation/v0",
            execution=LegacyExecution(
                status="baseline_drift",
                command=command,
                exit_code=None,
                stdout_valid_json=False,
                stderr="legacy baseline did not match; execution was not attempted",
                baseline=baseline,
            ),
            raw_legacy_result=None,
            normalized_legacy_observation=None,
        )
    pinned_paths = _pinned_paths(baseline_manifest)
    if not adapter_relative or adapter_relative not in pinned_paths:
        return LegacyObservation(
            schema_version="semantic-guard-legacy-observation/v0",
            execution=LegacyExecution(
                status="adapter_unpinned",
                command=command,
                exit_code=None,
                stdout_valid_json=False,
                stderr="legacy adapter must resolve inside the legacy root and be pinned by the selected manifest",
                baseline=baseline,
                adapter_pin_status="untrusted",
            ),
            raw_legacy_result=None,
            normalized_legacy_observation=None,
        )
    if not python.is_file() or not resolved_adapter.is_file():
        return LegacyObservation(
            schema_version="semantic-guard-legacy-observation/v0",
            execution=LegacyExecution(
                status="unavailable",
                command=command,
                exit_code=None,
                stdout_valid_json=False,
                stderr="legacy interpreter or adapter script is missing",
                baseline=baseline,
                adapter_pin_status="manifest_pinned",
            ),
            raw_legacy_result=None,
            normalized_legacy_observation=None,
        )

    payload = {
        "legacy_root": str(legacy_root),
        "text": text,
        "context": context,
        "strict": strict,
        "profile": profile,
        "logical_trace": logical_trace,
    }
    try:
        completed = subprocess.run(
            command,
            cwd=legacy_root,
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            capture_output=True,
            env=_normalized_legacy_environment(),
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return LegacyObservation(
            schema_version="semantic-guard-legacy-observation/v0",
            execution=LegacyExecution(
                status="execution_error",
                command=command,
                exit_code=None,
                stdout_valid_json=False,
                stderr=str(exc),
                baseline=baseline,
                adapter_pin_status="manifest_pinned",
            ),
            raw_legacy_result=None,
            normalized_legacy_observation=None,
        )

    raw: dict[str, Any] | None
    try:
        parsed = json.loads(completed.stdout)
        raw = parsed if isinstance(parsed, dict) else None
    except ValueError:
        raw = None
    valid_json = raw is not None
    schema_valid, schema_error = _validate_legacy_result(resolved_root, raw)
    post_baseline = check_baseline(resolved_root, baseline_manifest)
    drift_during_execution = (
        baseline.status == "matched"
        and (
            post_baseline.status != "matched"
            or post_baseline.manifest_sha256 != baseline.manifest_sha256
        )
    )
    if drift_during_execution:
        status = "baseline_drift_during_execution"
        effective_baseline = post_baseline
    else:
        status = (
            "completed"
            if completed.returncode == 0 and valid_json and schema_valid
            else "invalid_result"
        )
        effective_baseline = post_baseline
    stderr_parts = [completed.stderr[-4000:]]
    if schema_error:
        stderr_parts.append(schema_error)
    invocation = {
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "context_sha256": hashlib.sha256(context.encode("utf-8")).hexdigest(),
        "strict": strict,
        "profile": profile,
        "logical_trace": logical_trace,
        "timeout_seconds": timeout_seconds,
        "environment_profile": "semantic-guard-legacy-normalized/v0",
    }
    stdout_bytes = completed.stdout.encode("utf-8")
    return LegacyObservation(
        schema_version="semantic-guard-legacy-observation/v0",
        execution=LegacyExecution(
            status=status,
            command=command,
            exit_code=completed.returncode,
            stdout_valid_json=valid_json,
            stderr="\n".join(part for part in stderr_parts if part),
            baseline=effective_baseline,
            result_schema_valid=schema_valid,
            adapter_pin_status="manifest_pinned",
            invocation_fingerprint=invocation,
            stdout_sha256=hashlib.sha256(stdout_bytes).hexdigest(),
            stdout_bytes=len(stdout_bytes),
        ),
        raw_legacy_result=raw,
        normalized_legacy_observation=(
            normalize_legacy_result(raw)
            if raw is not None and schema_valid and not drift_during_execution
            else None
        ),
    )


def _finding_key(item: object) -> tuple[str, str, str, str]:
    if not isinstance(item, dict):
        return ("", "", str(item), "")
    return (
        str(item.get("rule_id", "")),
        str(item.get("category", "")),
        str(item.get("finding", "")),
        str(item.get("evidence", "")),
    )


def _sorted_dicts(items: object, *, key) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    values = [dict(item) for item in items if isinstance(item, dict)]
    return sorted(values, key=key)


def normalize_legacy_result(result: dict[str, Any]) -> dict[str, Any]:
    details = result.get("details") if isinstance(result.get("details"), dict) else {}
    relation = details.get("requirement_relation_summary")
    relation = relation if isinstance(relation, dict) else {}
    coverage = relation.get("coverage") if isinstance(relation.get("coverage"), dict) else {}
    applicability = relation.get("applicability") if isinstance(relation.get("applicability"), dict) else {}
    attempts = _sorted_dicts(
        relation.get("attempts"),
        key=lambda item: (
            str(item.get("stage", "")),
            str(item.get("provider_id", "")),
            str(item.get("status", "")),
        ),
    )
    checks = _sorted_dicts(
        relation.get("checks"),
        key=lambda item: (str(item.get("check_id", "")), str(item.get("obligation_id", ""))),
    )
    non_emitted = _sorted_dicts(
        details.get("non_emitted_rules"),
        key=lambda item: (
            str(item.get("rule_id", "")),
            str(item.get("emission_status", "")),
            str(item.get("reason", "")),
        ),
    )
    return {
        "top_level": {
            "legacy_status": result.get("status"),
            "legacy_score": result.get("score"),
            "phase": result.get("phase"),
        },
        "findings": _sorted_dicts(result.get("findings"), key=_finding_key),
        "missing": sorted({str(item) for item in result.get("missing", [])}),
        "next_actions": list(result.get("next_actions", [])),
        "relation": {
            "profile_ids": sorted({str(item) for item in relation.get("profile_ids", [])}),
            "extractor_stages": sorted({str(item) for item in relation.get("extractor_stages", [])}),
            "coverage": {
                "record_mode": coverage.get("record_mode"),
                "field_names": sorted({str(item) for item in coverage.get("field_names", [])}),
                "field_count": coverage.get("field_count"),
                "unresolved_span_count": coverage.get("unresolved_span_count"),
                "candidate_conflict_count": coverage.get("candidate_conflict_count"),
            },
            "applicability": {
                "status": applicability.get("status"),
                "reasons": sorted({str(item) for item in applicability.get("reasons", [])}),
            },
            "attempts": attempts,
            "obligation_checks": checks,
            "delta_counts_by_kind": dict(relation.get("delta_counts_by_kind", {})),
            "delta_counts_by_status": dict(relation.get("delta_counts_by_status", {})),
        },
        "non_emitted_rules": non_emitted,
    }
