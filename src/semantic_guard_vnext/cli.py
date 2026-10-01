from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from jsonschema import FormatChecker

from .assurance_graph import public_assurance_claim_v1
from .compat import project_legacy_result
from .audit.engine import audit_requirement_relations_vnext
from .governed_audit import project_governed_audit, wrap_legacy_output
from .governance_materials import default_candidate_governance_materials
from .japanese_dependency import GinzaDependencyProvider
from .japanese_morphology import SudachiMorphologyProvider
from .llm_candidates import SubmittedLLMCandidateProvider
from .legacy_runner import (
    MAX_REQUIREMENT_INPUT_BYTES,
    run_legacy_request,
    validate_requirement_input_size,
)
from .legacy_shadow_observation import build_legacy_shadow_observation
from .public_contract import (
    KNOWN_SCHEMA_NAMES,
    load_public_schema,
    public_audit_payload,
    validate_public_audit,
)
from .shadow import compare_with_legacy


EXIT_AUDIT_DISPOSITION = 3
EXIT_LEGACY_REQUIRED = 4
MAX_LLM_CANDIDATE_BUNDLE_BYTES = 1_048_576
MAX_GOVERNANCE_MATERIAL_BUNDLE_BYTES = 16_777_216


def _recorded_at(value: str) -> str:
    # Match the public schema's date-time format before any audit or shadow run.
    if not isinstance(value, str) or not FormatChecker().conforms(value, "date-time"):
        raise argparse.ArgumentTypeError(
            "must be an RFC 3339 date-time with a timezone (Z or an offset)"
        )
    return value


def _add_input(parser: argparse.ArgumentParser) -> None:
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--text", help="Requirement record text.")
    source.add_argument(
        "--file", type=Path, help="UTF-8 file. Reads stdin when omitted."
    )


def _add_analysis(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--analysis-mode",
        choices=("assurance", "conditional", "shadow_all"),
        default="assurance",
        help=(
            "Select the historical v0 provider schedule. This changes analysis "
            "observation only and grants no governed verdict authority; governed-v1 "
            "remains fail-closed regardless of this choice."
        ),
    )
    parser.add_argument(
        "--morphology",
        choices=("none", "sudachi"),
        default="none",
        help="Optional source-aligned morphology provider.",
    )
    parser.add_argument(
        "--dependency",
        choices=("none", "ginza"),
        default="none",
        help="Optional candidate-only dependency provider.",
    )
    parser.add_argument(
        "--llm-candidates",
        type=Path,
        help=(
            "Closed semantic-guard-vnext-llm-candidates/v0 JSON bundle from the "
            "calling agent. The bundle is candidate-only and must match the input digest."
        ),
    )


def _add_fail_on(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--fail-on",
        choices=("never", "warn", "block"),
        default=None,
        help=(
            "Return exit code 3 after emitting JSON when the workflow disposition "
            "meets this threshold. When omitted, governed output fails on warn; "
            "explicit legacy and shadow output report transport success only."
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="semantic-guard-vnext")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser(
        "audit-requirement",
        help="Audit one structured functional requirement under the vNext contract.",
    )
    _add_input(audit)
    _add_analysis(audit)
    _add_fail_on(audit)
    audit.add_argument(
        "--output",
        choices=(
            "governed-v1",
            "public",
            "legacy-public-v0",
            "legacy-assurance-v1",
            "legacy-compat",
            "legacy-internal-debug-v0",
        ),
        default="governed-v1",
        help=(
            "governed-v1/public is fail-closed and default; legacy-public-v0 "
            "exposes the historical ungoverned analysis contract only inside a "
            "self-describing observation-only envelope; legacy-internal-debug-v0 "
            "likewise isolates the historical report as nested legacy_payload."
        ),
    )
    audit.add_argument(
        "--recorded-at",
        type=_recorded_at,
        help="RFC 3339 observation time for reproducible public records.",
    )
    audit.add_argument(
        "--governance-materials",
        type=Path,
        help=(
            "Optional governance-material JSON. Values replace or extend the "
            "pinned H1/H2 candidates used by governed-v1; ENV and D7 material "
            "may be supplied here. Candidate material never grants authority."
        ),
    )

    shadow = subparsers.add_parser(
        "shadow-compare",
        help="Run vNext and a hash-pinned legacy process, then classify deltas.",
    )
    _add_input(shadow)
    _add_analysis(shadow)
    _add_fail_on(shadow)
    shadow.add_argument("--legacy-root", type=Path, default=Path.cwd())
    shadow.add_argument("--baseline-manifest", type=Path)
    shadow.add_argument("--legacy-adapter", type=Path)
    shadow.add_argument("--legacy-profile", default="default")
    shadow.add_argument("--legacy-logical-trace", default="summary")
    shadow.add_argument("--timeout-seconds", type=float, default=30.0)
    shadow.add_argument("--allow-baseline-drift", action="store_true")
    shadow.add_argument("--require-legacy", action="store_true")
    shadow.add_argument("--recorded-at", type=_recorded_at)

    schema = subparsers.add_parser(
        "schema", help="Print one known vNext contract schema."
    )
    schema.add_argument(
        "name",
        choices=tuple(sorted(KNOWN_SCHEMA_NAMES)),
        default="audit-result",
        nargs="?",
    )
    return parser


def _read_text(args: argparse.Namespace, parser: argparse.ArgumentParser) -> str:
    if args.text is not None:
        text = args.text
        try:
            validate_requirement_input_size(text)
        except ValueError as exc:
            parser.error(str(exc))
        return text
    if args.file is not None:
        try:
            if args.file.stat().st_size > MAX_REQUIREMENT_INPUT_BYTES:
                parser.error(
                    f"requirement input exceeds {MAX_REQUIREMENT_INPUT_BYTES} UTF-8 bytes"
                )
            data = args.file.read_bytes()
        except OSError as exc:
            parser.error(f"could not read {args.file}: {exc}")
        return _decode_bounded_input(data, parser, source=str(args.file))

    binary_stdin = getattr(sys.stdin, "buffer", None)
    if binary_stdin is not None:
        data = binary_stdin.read(MAX_REQUIREMENT_INPUT_BYTES + 1)
        return _decode_bounded_input(data, parser, source="stdin")

    text = sys.stdin.read(MAX_REQUIREMENT_INPUT_BYTES + 1)
    try:
        validate_requirement_input_size(text)
    except ValueError as exc:
        parser.error(str(exc))
    return text


def _decode_bounded_input(
    data: bytes,
    parser: argparse.ArgumentParser,
    *,
    source: str,
) -> str:
    if len(data) > MAX_REQUIREMENT_INPUT_BYTES:
        parser.error(
            f"requirement input exceeds {MAX_REQUIREMENT_INPUT_BYTES} UTF-8 bytes"
        )
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        parser.error(f"{source} is not valid UTF-8: {exc}")


def _disposition_exit(workflow: str, fail_on: str) -> int:
    if fail_on == "warn" and workflow in {"warn", "block"}:
        return EXIT_AUDIT_DISPOSITION
    if fail_on == "block" and workflow == "block":
        return EXIT_AUDIT_DISPOSITION
    return 0


def _providers(args: argparse.Namespace, parser: argparse.ArgumentParser):
    morphology = SudachiMorphologyProvider() if args.morphology == "sudachi" else None
    dependency = GinzaDependencyProvider() if args.dependency == "ginza" else None
    llm = None
    if args.llm_candidates is not None:
        try:
            data = args.llm_candidates.read_bytes()
        except OSError as exc:
            parser.error(f"could not read LLM candidate bundle: {exc}")
        if len(data) > MAX_LLM_CANDIDATE_BUNDLE_BYTES:
            parser.error(
                "LLM candidate bundle exceeds "
                f"{MAX_LLM_CANDIDATE_BUNDLE_BYTES} UTF-8 bytes"
            )
        try:
            bundle = json.loads(data.decode("utf-8"))
            if not isinstance(bundle, dict):
                raise ValueError("bundle root must be an object")
            llm = SubmittedLLMCandidateProvider(bundle)
        except (UnicodeDecodeError, ValueError) as exc:
            parser.error(f"invalid LLM candidate bundle: {exc}")
        except Exception as exc:
            # jsonschema.ValidationError is intentionally rendered through the
            # CLI contract without importing its concrete type here.
            parser.error(f"invalid LLM candidate bundle: {exc}")
    return morphology, dependency, llm


def _governance_materials(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> dict[str, object]:
    materials: dict[str, object] = default_candidate_governance_materials()
    path = args.governance_materials
    if path is None:
        return materials
    try:
        data = path.read_bytes()
    except OSError as exc:
        parser.error(f"could not read governance material bundle: {exc}")
    if len(data) > MAX_GOVERNANCE_MATERIAL_BUNDLE_BYTES:
        parser.error(
            "governance material bundle exceeds "
            f"{MAX_GOVERNANCE_MATERIAL_BUNDLE_BYTES} UTF-8 bytes"
        )
    try:
        supplied = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        parser.error(f"invalid governance material bundle: {exc}")
    if not isinstance(supplied, dict):
        parser.error("governance material bundle root must be an object")
    materials.update(supplied)
    return materials


def _write(payload: object) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    sys.stdout.write("\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "schema":
        _write(load_public_schema(args.name))
        return 0

    text = _read_text(args, parser)
    morphology, dependency, llm = _providers(args, parser)
    report = audit_requirement_relations_vnext(
        text,
        morphology_provider=morphology,
        dependency_provider=dependency,
        llm_provider=llm,
        analysis_mode=args.analysis_mode,
    )

    if args.command == "audit-requirement":
        if args.governance_materials is not None and args.output not in {
            "governed-v1",
            "public",
        }:
            parser.error(
                "--governance-materials is valid only for governed-v1/public output"
            )
        if args.output == "legacy-compat":
            payload = wrap_legacy_output(
                args.output,
                project_legacy_result(report),
            )
        elif args.output == "legacy-assurance-v1":
            payload = wrap_legacy_output(
                args.output,
                public_assurance_claim_v1(report, recorded_at=args.recorded_at),
            )
        elif args.output == "legacy-internal-debug-v0":
            payload = wrap_legacy_output(args.output, report.as_dict())
        elif args.output == "legacy-public-v0":
            legacy_payload = public_audit_payload(report, recorded_at=args.recorded_at)
            validate_public_audit(legacy_payload)
            payload = wrap_legacy_output(args.output, legacy_payload)
        else:
            try:
                payload = project_governed_audit(
                    report,
                    governance_materials=_governance_materials(args, parser),
                    recorded_at=args.recorded_at,
                )
            except ValueError as exc:
                parser.error(f"governance material assessment failed: {exc}")
        _write(payload)
        workflow = (
            payload["assurance_assessment"]["workflow_disposition"]
            if args.output in {"governed-v1", "public"}
            else report.result.workflow.value
        )
        fail_on = args.fail_on
        if fail_on is None:
            fail_on = "warn" if args.output in {"governed-v1", "public"} else "never"
        return _disposition_exit(workflow, fail_on)

    legacy_root = args.legacy_root.resolve()
    baseline = (
        args.baseline_manifest.resolve()
        if args.baseline_manifest
        else legacy_root / "vnext" / "migration" / "legacy-baseline-2026-07-16.json"
    )
    adapter = (
        args.legacy_adapter.resolve()
        if args.legacy_adapter
        else legacy_root / "vnext" / "scripts" / "legacy_request_adapter.py"
    )
    legacy = run_legacy_request(
        text=text,
        profile=args.legacy_profile,
        logical_trace=args.legacy_logical_trace,
        legacy_root=legacy_root,
        baseline_manifest=baseline,
        adapter_script=adapter,
        timeout_seconds=args.timeout_seconds,
        allow_baseline_drift=args.allow_baseline_drift,
    )
    native = public_audit_payload(report, recorded_at=args.recorded_at)
    validate_public_audit(native)
    comparison = compare_with_legacy(report, legacy)
    _write(
        build_legacy_shadow_observation(
            vnext=native,
            legacy=legacy.as_dict(),
            comparison=comparison.as_dict(),
        )
    )
    if args.require_legacy and (
        legacy.execution.status != "completed"
        or legacy.execution.baseline.status != "matched"
        or not legacy.execution.result_schema_valid
        or legacy.execution.adapter_pin_status != "manifest_pinned"
    ):
        return EXIT_LEGACY_REQUIRED
    return _disposition_exit(report.result.workflow.value, args.fail_on or "never")


if __name__ == "__main__":
    raise SystemExit(main())
