#!/usr/bin/env python3
"""Create or verify CI-internal source-to-distribution binding sidecars.

The record binds one wheel and one source distribution to the exact clean Git
commit and tree from which they were built.  It is an integrity and identity
check inside one build context, not a signature or external provenance proof.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import tomllib
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "semantic-guard-distribution-binding/v0"
MANIFEST_FILENAME = "distribution-binding.json"
CHECKSUMS_FILENAME = "SHA256SUMS"
MAX_PROJECT_FILE_BYTES = 1024 * 1024
MAX_SIDECAR_BYTES = 1024 * 1024
MAX_ARTIFACT_BYTES = 256 * 1024 * 1024
_HEX_OID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SAFE_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+!-]*\Z")
_SAFE_FILENAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+!-]*\Z")
_LIMITATIONS = (
    "This record binds local artifact bytes to one clean tracked Git commit and tree; "
    "it is not a signature or external authenticity proof.",
    "Dependency provenance, SBOM, field validity, operational qualification, security "
    "certification, release approval, and human acceptance are outside this record.",
)


class BindingFailure(RuntimeError):
    """Fail-closed distribution binding error with a stable diagnostic code."""

    def __init__(self, code: str, message: str, *, details: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


@dataclass(frozen=True)
class ProjectIdentity:
    name: str
    version: str
    normalized_name: str


@dataclass(frozen=True)
class ArtifactIdentity:
    kind: str
    filename: str
    sha256: str
    size_bytes: int

    def as_record(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "filename": self.filename,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def _validate_plain_filename(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise BindingFailure("unsafe_filename", "artifact filename must be a non-empty string")
    path = Path(value)
    if (
        path.name != value
        or path.is_absolute()
        or "/" in value
        or "\\" in value
        or value in {".", ".."}
        or _SAFE_FILENAME.fullmatch(value) is None
    ):
        raise BindingFailure(
            "unsafe_filename",
            f"artifact filename must stay inside the distribution directory: {value!r}",
        )
    return value


def _validate_oid(value: str, *, label: str) -> str:
    if _HEX_OID.fullmatch(value) is None:
        raise BindingFailure(
            "git_oid_invalid",
            f"{label} must be a lowercase 40- or 64-character Git object id",
            details={"label": label},
        )
    return "git-sha1" if len(value) == 40 else "git-sha256"


def _read_bounded_regular_file(
    path: Path,
    *,
    maximum_bytes: int,
    unavailable_code: str,
) -> bytes:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise BindingFailure(unavailable_code, f"could not inspect {path.name}: {exc}") from exc
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise BindingFailure(unavailable_code, f"{path.name} must be a non-symlink regular file")
    if metadata.st_size <= 0 or metadata.st_size > maximum_bytes:
        raise BindingFailure(
            unavailable_code,
            f"{path.name} size must be within 1..{maximum_bytes} bytes",
            details={"observed_bytes": metadata.st_size},
        )
    return path.read_bytes()


def _load_project_identity(project_root: Path) -> ProjectIdentity:
    pyproject = project_root / "pyproject.toml"
    encoded = _read_bounded_regular_file(
        pyproject,
        maximum_bytes=MAX_PROJECT_FILE_BYTES,
        unavailable_code="project_metadata_unavailable",
    )
    try:
        document = tomllib.loads(encoded.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise BindingFailure(
            "project_metadata_invalid",
            f"pyproject.toml is invalid: {exc}",
        ) from exc
    project = document.get("project")
    if not isinstance(project, dict):
        raise BindingFailure("project_identity_invalid", "pyproject.toml has no [project] table")
    name = project.get("name")
    version = project.get("version")
    if not isinstance(name, str) or not name.strip():
        raise BindingFailure("project_identity_invalid", "project.name must be a non-empty string")
    if not isinstance(version, str) or _SAFE_VERSION.fullmatch(version) is None:
        raise BindingFailure(
            "project_identity_invalid",
            "project.version is not a safe filename token",
        )
    normalized_name = re.sub(r"[-_.]+", "_", name).lower()
    if not normalized_name or re.fullmatch(r"[a-z0-9_]+", normalized_name) is None:
        raise BindingFailure(
            "project_identity_invalid",
            "project.name cannot form a distribution filename",
        )
    return ProjectIdentity(name=name, version=version, normalized_name=normalized_name)


def _validate_distribution_directory(dist_dir: Path) -> Path:
    try:
        metadata = dist_dir.lstat()
    except OSError as exc:
        raise BindingFailure(
            "distribution_directory_unavailable",
            f"could not inspect distribution directory: {exc}",
        ) from exc
    if dist_dir.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise BindingFailure(
            "distribution_directory_invalid",
            "distribution directory must be a non-symlink directory",
        )
    return dist_dir.resolve(strict=True)


def _artifact_identity(path: Path, *, kind: str) -> ArtifactIdentity:
    filename = _validate_plain_filename(path.name)
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise BindingFailure("artifact_unavailable", f"could not inspect {filename}: {exc}") from exc
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise BindingFailure("artifact_unavailable", f"{filename} must be a regular file")
    if metadata.st_size <= 0 or metadata.st_size > MAX_ARTIFACT_BYTES:
        raise BindingFailure(
            "artifact_unavailable",
            f"{filename} size must be within 1..{MAX_ARTIFACT_BYTES} bytes",
            details={"observed_bytes": metadata.st_size},
        )
    return ArtifactIdentity(
        kind=kind,
        filename=filename,
        sha256=_sha256(path),
        size_bytes=metadata.st_size,
    )


def _discover_artifacts(dist_dir: Path, project: ProjectIdentity) -> tuple[ArtifactIdentity, ...]:
    entries = tuple(dist_dir.iterdir())
    wheel_paths = sorted(
        (path for path in entries if path.name.casefold().endswith(".whl")),
        key=lambda path: path.name,
    )
    sdist_paths = sorted(
        (path for path in entries if path.name.casefold().endswith(".tar.gz")),
        key=lambda path: path.name,
    )
    recognized_names = {
        *(path.name for path in wheel_paths),
        *(path.name for path in sdist_paths),
        MANIFEST_FILENAME,
        CHECKSUMS_FILENAME,
    }
    unexpected_names = sorted(path.name for path in entries if path.name not in recognized_names)
    if unexpected_names:
        raise BindingFailure(
            "artifact_set_invalid",
            "distribution directory contains an unexpected member",
            details={"unexpected": unexpected_names},
        )
    if len(wheel_paths) != 1 or len(sdist_paths) != 1:
        raise BindingFailure(
            "artifact_count_invalid",
            "distribution directory must contain exactly one wheel and one source distribution",
            details={"wheel_count": len(wheel_paths), "sdist_count": len(sdist_paths)},
        )
    wheel = wheel_paths[0]
    sdist = sdist_paths[0]
    expected_prefix = f"{project.normalized_name}-{project.version}"
    if not wheel.name.startswith(expected_prefix + "-") or not wheel.name.endswith(".whl"):
        raise BindingFailure(
            "artifact_name_mismatch",
            f"wheel filename does not match {project.name} {project.version}",
            details={"filename": wheel.name},
        )
    expected_sdist = expected_prefix + ".tar.gz"
    if sdist.name != expected_sdist:
        raise BindingFailure(
            "artifact_name_mismatch",
            f"source distribution filename must be {expected_sdist}",
            details={"filename": sdist.name},
        )
    return tuple(
        sorted(
            (
                _artifact_identity(sdist, kind="sdist"),
                _artifact_identity(wheel, kind="wheel"),
            ),
            key=lambda item: item.kind,
        )
    )


def _build_manifest(
    project_root: Path,
    dist_dir: Path,
    *,
    source_commit: str,
    source_tree: str,
) -> tuple[dict[str, object], tuple[ArtifactIdentity, ...]]:
    project = _load_project_identity(project_root)
    artifacts = _discover_artifacts(dist_dir, project)
    commit_algorithm = _validate_oid(source_commit, label="source commit")
    tree_algorithm = _validate_oid(source_tree, label="source tree")
    if commit_algorithm != tree_algorithm:
        raise BindingFailure("git_oid_mismatch", "commit and tree use different Git object formats")
    manifest: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "project": {"name": project.name, "version": project.version},
        "source": {
            "commit": {"algorithm": commit_algorithm, "value": source_commit},
            "tree": {"algorithm": tree_algorithm, "value": source_tree},
            "tracked_worktree": "clean",
        },
        "artifacts": [item.as_record() for item in artifacts],
        "limitations": list(_LIMITATIONS),
    }
    return manifest, artifacts


def _checksums_text(
    artifacts: tuple[ArtifactIdentity, ...],
    manifest_bytes: bytes,
) -> str:
    entries = [(item.filename, item.sha256) for item in artifacts]
    entries.append((MANIFEST_FILENAME, _sha256_bytes(manifest_bytes)))
    return "".join(f"{digest}  {filename}\n" for filename, digest in sorted(entries))


def _atomic_write(path: Path, value: bytes) -> None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise BindingFailure("sidecar_path_invalid", f"{path.name} is not a regular file")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{path.name}.",
            dir=path.parent,
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
        temporary = None
    except OSError as exc:
        raise BindingFailure("sidecar_write_failed", f"could not write {path.name}: {exc}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _expect_exact_keys(value: Mapping[str, Any], expected: set[str], *, label: str) -> None:
    if set(value) != expected:
        raise BindingFailure(
            "manifest_shape_invalid",
            f"{label} fields differ from the v0 contract",
            details={"observed": sorted(value), "expected": sorted(expected)},
        )


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise BindingFailure(
                "manifest_json_invalid",
                f"manifest JSON contains a duplicate key: {key!r}",
            )
        value[key] = item
    return value


def _validate_manifest_shape(value: object) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise BindingFailure("manifest_shape_invalid", "manifest root must be an object")
    _expect_exact_keys(
        value,
        {"schema_version", "project", "source", "artifacts", "limitations"},
        label="manifest",
    )
    if value.get("schema_version") != SCHEMA_VERSION:
        raise BindingFailure("manifest_schema_invalid", "manifest schema_version is not supported")
    project = value.get("project")
    source = value.get("source")
    artifacts = value.get("artifacts")
    limitations = value.get("limitations")
    if not isinstance(project, dict) or not isinstance(source, dict):
        raise BindingFailure("manifest_shape_invalid", "project and source must be objects")
    _expect_exact_keys(project, {"name", "version"}, label="project")
    _expect_exact_keys(source, {"commit", "tree", "tracked_worktree"}, label="source")
    if source.get("tracked_worktree") != "clean":
        raise BindingFailure("manifest_source_invalid", "tracked_worktree must be clean")
    for label in ("commit", "tree"):
        identity = source.get(label)
        if not isinstance(identity, dict):
            raise BindingFailure("manifest_source_invalid", f"source.{label} must be an object")
        _expect_exact_keys(identity, {"algorithm", "value"}, label=f"source.{label}")
        observed = identity.get("value")
        if not isinstance(observed, str):
            raise BindingFailure(
                "manifest_source_invalid",
                f"source.{label}.value must be a string",
            )
        expected_algorithm = _validate_oid(observed, label=f"source {label}")
        if identity.get("algorithm") != expected_algorithm:
            raise BindingFailure(
                "manifest_source_invalid",
                f"source.{label}.algorithm is inconsistent",
            )
    if not isinstance(artifacts, list) or len(artifacts) != 2:
        raise BindingFailure(
            "manifest_shape_invalid",
            "manifest must contain exactly two artifacts",
        )
    observed_kinds: set[str] = set()
    observed_names: set[str] = set()
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            raise BindingFailure("manifest_shape_invalid", f"artifacts[{index}] must be an object")
        _expect_exact_keys(artifact, {"kind", "filename", "sha256", "size_bytes"}, label="artifact")
        kind = artifact.get("kind")
        filename = _validate_plain_filename(artifact.get("filename"))
        digest = artifact.get("sha256")
        size_bytes = artifact.get("size_bytes")
        if kind not in {"wheel", "sdist"} or kind in observed_kinds:
            raise BindingFailure(
                "manifest_artifact_invalid",
                "artifact kinds must be unique wheel and sdist",
            )
        if filename in observed_names:
            raise BindingFailure("manifest_artifact_invalid", "artifact filenames must be unique")
        if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
            raise BindingFailure("manifest_artifact_invalid", "artifact sha256 is invalid")
        if not isinstance(size_bytes, int) or isinstance(size_bytes, bool) or size_bytes <= 0:
            raise BindingFailure(
                "manifest_artifact_invalid",
                "artifact size_bytes must be positive",
            )
        observed_kinds.add(kind)
        observed_names.add(filename)
    if observed_kinds != {"wheel", "sdist"}:
        raise BindingFailure("manifest_artifact_invalid", "manifest must contain wheel and sdist")
    if limitations != list(_LIMITATIONS):
        raise BindingFailure("manifest_limitations_invalid", "manifest limitations differ from v0")
    return value


def create_binding(
    project_root: str | Path,
    dist_dir: str | Path,
    *,
    source_commit: str,
    source_tree: str,
) -> dict[str, object]:
    root = Path(project_root).resolve(strict=True)
    distribution = _validate_distribution_directory(Path(dist_dir))
    manifest, artifacts = _build_manifest(
        root,
        distribution,
        source_commit=source_commit,
        source_tree=source_tree,
    )
    manifest_bytes = _canonical_json(manifest).encode("utf-8")
    checksums_bytes = _checksums_text(artifacts, manifest_bytes).encode("utf-8")
    _atomic_write(distribution / MANIFEST_FILENAME, manifest_bytes)
    _atomic_write(distribution / CHECKSUMS_FILENAME, checksums_bytes)
    return check_binding(
        root,
        distribution,
        source_commit=source_commit,
        source_tree=source_tree,
    )


def check_binding(
    project_root: str | Path,
    dist_dir: str | Path,
    *,
    source_commit: str,
    source_tree: str,
) -> dict[str, object]:
    root = Path(project_root).resolve(strict=True)
    distribution = _validate_distribution_directory(Path(dist_dir))
    expected, artifacts = _build_manifest(
        root,
        distribution,
        source_commit=source_commit,
        source_tree=source_tree,
    )
    manifest_path = distribution / MANIFEST_FILENAME
    checksums_path = distribution / CHECKSUMS_FILENAME
    manifest_bytes = _read_bounded_regular_file(
        manifest_path,
        maximum_bytes=MAX_SIDECAR_BYTES,
        unavailable_code="manifest_unavailable",
    )
    checksums_bytes = _read_bounded_regular_file(
        checksums_path,
        maximum_bytes=MAX_SIDECAR_BYTES,
        unavailable_code="checksums_unavailable",
    )
    try:
        observed = json.loads(manifest_bytes, object_pairs_hook=_reject_duplicate_json_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BindingFailure("manifest_json_invalid", f"manifest JSON is invalid: {exc}") from exc
    _validate_manifest_shape(observed)
    expected_manifest_bytes = _canonical_json(expected).encode("utf-8")
    if observed != expected or manifest_bytes != expected_manifest_bytes:
        raise BindingFailure(
            "manifest_mismatch",
            "distribution manifest does not match project, source, or artifact bytes",
        )
    expected_checksums = _checksums_text(artifacts, expected_manifest_bytes).encode("utf-8")
    if checksums_bytes != expected_checksums:
        raise BindingFailure("checksums_mismatch", "SHA256SUMS differs from the bound artifacts")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "pass",
        "subject": {
            "manifest": str(manifest_path),
            "manifest_sha256": _sha256_bytes(manifest_bytes),
            "checksums": str(checksums_path),
            "artifacts": [item.as_record() for item in artifacts],
            "source_commit": source_commit,
            "source_tree": source_tree,
        },
        "limitations": list(_LIMITATIONS),
        "errors": [],
    }


def _git_output(project_root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(project_root), *arguments],
        text=True,
        capture_output=True,
        check=False,
        timeout=15.0,
    )
    if completed.returncode != 0:
        raise BindingFailure(
            "git_inspection_failed",
            f"git {' '.join(arguments)} failed",
            details={"stderr": completed.stderr[-4096:]},
        )
    return completed.stdout.strip()


def _source_identity_from_clean_git(
    project_root: Path,
    *,
    expected_commit: str | None,
) -> tuple[str, str]:
    top_level = Path(_git_output(project_root, "rev-parse", "--show-toplevel")).resolve(strict=True)
    if top_level != project_root:
        raise BindingFailure("git_root_mismatch", "project root must equal the Git worktree root")
    status = _git_output(project_root, "status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise BindingFailure(
            "git_worktree_dirty",
            "tracked source and unignored files must be clean before binding distributions",
            details={"status": status.splitlines()[:20]},
        )
    commit = _git_output(project_root, "rev-parse", "HEAD")
    tree = _git_output(project_root, "rev-parse", "HEAD^{tree}")
    _validate_oid(commit, label="source commit")
    _validate_oid(tree, label="source tree")
    if expected_commit is not None and expected_commit != commit:
        raise BindingFailure(
            "expected_commit_mismatch",
            "expected commit differs from checked-out HEAD",
            details={"expected": expected_commit, "observed": commit},
        )
    return commit, tree


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("create", "check"))
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--dist-dir", type=Path, default=Path("dist"))
    parser.add_argument("--expected-commit")
    return parser


def _json_print(value: Mapping[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = build_parser().parse_args(argv)
        root = arguments.project_root.resolve(strict=True)
        dist_dir = arguments.dist_dir
        if not dist_dir.is_absolute():
            dist_dir = root / dist_dir
        commit, tree = _source_identity_from_clean_git(
            root,
            expected_commit=arguments.expected_commit,
        )
        operation = create_binding if arguments.mode == "create" else check_binding
        result = operation(root, dist_dir, source_commit=commit, source_tree=tree)
    except BindingFailure as exc:
        _json_print(
            {
                "schema_version": SCHEMA_VERSION,
                "status": "error",
                "subject": None,
                "limitations": ["No distribution binding may be inferred from an error result."],
                "errors": [
                    {
                        "code": exc.code,
                        "message": str(exc),
                        "details": exc.details,
                    }
                ],
            }
        )
        return 1
    except Exception as exc:
        _json_print(
            {
                "schema_version": SCHEMA_VERSION,
                "status": "error",
                "subject": None,
                "limitations": ["No distribution binding may be inferred from an error result."],
                "errors": [
                    {
                        "code": "unexpected_binding_error",
                        "message": f"{type(exc).__name__}: {exc}",
                        "details": {},
                    }
                ],
            }
        )
        return 1
    _json_print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
