from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess


SCHEMA_VERSION = "semantic-guard-legacy-baseline/v1"
PIN_PROFILE = "semantic-guard-requirement-relations-legacy/v1"
SCOPES = (
    ("src/semantic_guard", (".py",)),
    ("schemas", (".json",)),
    ("docs/conventions", (".json", ".md")),
    ("docs/prototypes", (".md",)),
    ("skills/semantic-implementation", (".md", ".yaml", ".yml")),
    ("tests", (".diff", ".json", ".md", ".py")),
)
EXACT_PATHS = (
    ".github/workflows/ci.yml",
    "LICENSE",
    "README.md",
    "pyproject.toml",
    "uv.lock",
    "vnext/scripts/legacy_request_adapter.py",
)
IGNORED_PARTS = frozenset({"__pycache__", ".pytest_cache"})


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _covered_paths(root: Path) -> list[Path]:
    paths = {root / relative for relative in EXACT_PATHS}
    for relative_root, suffixes in SCOPES:
        scope_root = root / relative_root
        if not scope_root.is_dir():
            raise SystemExit(f"missing baseline scope: {relative_root}")
        for candidate in scope_root.rglob("*"):
            if not candidate.is_file():
                continue
            relative = candidate.relative_to(root)
            if any(part in IGNORED_PARTS for part in relative.parts):
                continue
            if candidate.suffix in suffixes:
                paths.add(candidate)
    missing = [path for path in paths if not path.is_file()]
    if missing:
        rendered = ", ".join(str(path.relative_to(root)) for path in sorted(missing))
        raise SystemExit(f"missing exact baseline paths: {rendered}")
    return sorted(paths, key=lambda path: path.relative_to(root).as_posix())


def _manifest(root: Path) -> dict[str, object]:
    paths = _covered_paths(root)
    interpreter = root / ".venv" / "bin" / "python"
    if not interpreter.is_file():
        raise SystemExit("missing legacy interpreter: .venv/bin/python")
    version = subprocess.run(
        [str(interpreter), "-VV"],
        cwd=root,
        text=True,
        capture_output=True,
        timeout=10.0,
        check=True,
    )
    python_version = (version.stdout + version.stderr).strip()
    if not python_version:
        raise SystemExit("legacy interpreter returned an empty version string")
    return {
        "schema_version": SCHEMA_VERSION,
        "pin_profile": PIN_PROFILE,
        "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "capture_authority": {
            "status": "pending_human_acceptance",
            "statement": (
                "This is a complete-scope working-tree capture, not proof that the "
                "working tree itself was historically correct or uncompromised."
            ),
        },
        "version_control_state": {
            "status": "unavailable",
            "reason": "source root is not a Git repository",
        },
        "runtime": {
            "interpreter_path": ".venv/bin/python",
            "resolved_path_observation": str(interpreter.resolve()),
            "sha256": _sha256(interpreter),
            "python_version": python_version,
            "limits": (
                "The executable hash and lockfile detect ordinary runtime drift; "
                "they do not attest the operating system, dynamic libraries, or host."
            ),
        },
        "coverage": {
            "scopes": [
                {"root": relative_root, "suffixes": list(suffixes)}
                for relative_root, suffixes in SCOPES
            ],
            "exact_paths": list(EXACT_PATHS),
            "closure_rule": (
                "Every matching live file and every exact path must appear in "
                "source_digests; additions, removals, and content changes are drift."
            ),
        },
        "source_digests": [
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": _sha256(path),
            }
            for path in paths
        ],
        "verification_reference": (
            "Verification observations are recorded separately under vnext/validation; "
            "the capture tool does not claim commands it did not execute."
        ),
        "known_test_failures": [
            {
                "test": "test_aligned_public_evidence_uses_the_unique_verifies_pair",
                "observed": (
                    "verification excerpt included the full method sentence instead "
                    "of the expected bounded terms"
                ),
            },
            {
                "test": "test_asserted_verification_dimension_mismatch_is_derived_and_not_satisfied",
                "observed": "verification mismatch status was candidate instead of derived",
            },
        ],
        "known_semantic_failures": [
            "top-level pass can coexist with unknown relation applicability and open-text coverage",
            "quoted, reported, unadopted, or negated structured values can be treated as satisfied",
            "the unresolved decision is global rather than obligation-scoped",
            "morphology, dependency, and LLM stages do not re-evaluate obligation outcomes",
            "provider output cannot release or apply a hold through a versioned policy",
        ],
        "interpretation": (
            "This record is a migration observation and drift detector, not a "
            "correctness oracle, provenance signature, or release approval."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture a closed legacy migration baseline after explicit trust-root review."
    )
    parser.add_argument("--legacy-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--acknowledge-new-trust-root", action="store_true")
    args = parser.parse_args()
    if not args.acknowledge_new_trust_root:
        parser.error("--acknowledge-new-trust-root is required")

    root = args.legacy_root.resolve()
    output = args.output.resolve()
    try:
        output.relative_to(root)
    except ValueError as exc:
        raise SystemExit("output must remain inside the legacy root") from exc
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(_manifest(root), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
