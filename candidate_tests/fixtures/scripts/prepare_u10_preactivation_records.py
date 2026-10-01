#!/usr/bin/env python3
"""Observe and resolve the U-10 worker principal selected by a human record.

This program never creates a human decision.  ``observe`` reads an existing,
sealed U-10 preactivation decision and records the selected local OS account and
host.  ``resolve`` joins that exact decision to that exact observation after a
fresh OS re-observation.  Both outputs are candidate evidence with no execution
or assurance authority.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import pwd
import sys
from typing import Any

import prepare_u10_root_candidate as candidate


def _load_object(path: Path, *, code: str) -> tuple[dict[str, Any], bytes, Path]:
    raw, resolved, _observed = candidate._read_stable_regular(path)
    try:
        value = candidate.strict_json_loads(raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise candidate.CandidateBoundaryError(code, str(path)) from exc
    if not isinstance(value, dict):
        raise candidate.CandidateBoundaryError(code, str(path))
    return value, raw, resolved


def _write_candidate_record(path: Path, value: Mapping[str, Any]) -> bytes:
    encoded = candidate.canonical_json_bytes(value) + b"\n"
    exact_parent = path.parent.resolve(strict=True)
    exact = exact_parent / path.name
    if exact == exact_parent or path.name in {"", ".", ".."}:
        raise candidate.CandidateBoundaryError(
            "preactivation_output_path_invalid", str(path)
        )
    candidate._write_exclusive(exact, encoded, mode=0o600)
    candidate._fsync_directory_v1(
        exact_parent, code="preactivation_output_directory_fsync_failed"
    )
    return encoded


def observe(
    *, decision_path: Path, output: Path, account_name: str | None
) -> dict[str, Any]:
    decision, decision_raw, decision_resolved = _load_object(
        decision_path, code="preactivation_decision_unreadable"
    )
    candidate.validate_preactivation_decision_v1(decision)
    selection = decision["worker_identity_selection"]
    if selection == "current_user_501_20_empty_supplementary_groups":
        selected_account = account_name or pwd.getpwuid(501).pw_name
    elif selection == "dedicated_non_login_service_principal":
        if account_name is None:
            raise candidate.CandidateBoundaryError(
                "preactivation_dedicated_account_required", "--account"
            )
        selected_account = account_name
    else:
        raise candidate.CandidateBoundaryError(
            "preactivation_worker_observation_not_applicable", str(selection)
        )
    observation = candidate.build_worker_account_observation_v1(
        decision=decision,
        decision_raw=decision_raw,
        decision_locator=decision_resolved,
        account_name=selected_account,
    )
    encoded = _write_candidate_record(output, observation)
    return {
        "status": "worker_account_observed_candidate_only",
        "record_id": observation["observation_id"],
        "output": str(output.parent.resolve(strict=True) / output.name),
        "artifact_digest": candidate.digest_bytes(encoded),
        "semantic_digest": observation["observation_digest"],
        "human_decision_created": False,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }


def resolve(
    *, decision_path: Path, observation_path: Path, output: Path
) -> dict[str, Any]:
    decision, decision_raw, decision_resolved = _load_object(
        decision_path, code="preactivation_decision_unreadable"
    )
    observation, observation_raw, observation_resolved = _load_object(
        observation_path, code="preactivation_worker_observation_unreadable"
    )
    resolution = candidate.build_worker_principal_resolution_v1(
        decision=decision,
        decision_raw=decision_raw,
        decision_locator=decision_resolved,
        observation=observation,
        observation_raw=observation_raw,
        observation_locator=observation_resolved,
    )
    encoded = _write_candidate_record(output, resolution)
    return {
        "status": "worker_principal_resolved_candidate_only",
        "record_id": resolution["resolution_id"],
        "output": str(output.parent.resolve(strict=True) / output.name),
        "artifact_digest": candidate.digest_bytes(encoded),
        "semantic_digest": resolution["resolution_digest"],
        "human_decision_created": False,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    observe_parser = subparsers.add_parser(
        "observe", help="observe the OS account selected by an existing decision"
    )
    observe_parser.add_argument("--decision", type=Path, required=True)
    observe_parser.add_argument("--account")
    observe_parser.add_argument("--output", type=Path, required=True)
    resolve_parser = subparsers.add_parser(
        "resolve", help="join an exact decision to an exact account observation"
    )
    resolve_parser.add_argument("--decision", type=Path, required=True)
    resolve_parser.add_argument("--observation", type=Path, required=True)
    resolve_parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "observe":
            result = observe(
                decision_path=arguments.decision,
                output=arguments.output,
                account_name=arguments.account,
            )
        else:
            result = resolve(
                decision_path=arguments.decision,
                observation_path=arguments.observation,
                output=arguments.output,
            )
    except (candidate.CandidateBoundaryError, OSError, KeyError) as exc:
        code = getattr(exc, "code", "preactivation_record_operation_failed")
        print(
            json.dumps(
                {"status": "error", "error": {"code": code, "detail": str(exc)}},
                ensure_ascii=False,
                sort_keys=True,
                allow_nan=False,
            ),
            file=sys.stderr,
        )
        return 2
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
