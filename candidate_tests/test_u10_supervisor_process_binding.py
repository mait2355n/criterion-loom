from __future__ import annotations

import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import Mock, patch

from semantic_guard_u10_broker.protected_io import BrokerBoundaryError
from semantic_guard_u10_broker.supervisor import (
    _ensure_worker_process_group_quiescent,
    _observe_launched_worker_process,
    _validate_worker_outcome,
    _write_exclusive,
)


def _context() -> dict:
    return {
        "request": {
            "entry_id": "entry.u10.test",
            "command_id": "verify.u10.test",
            "request_nonce": "a" * 64,
        },
        "snapshot": {
            "worker_identity": {
                "uid": 501,
                "gid": 20,
                "account_supplementary_gids": [12, 61],
                "effective_supplementary_gids": [],
                "umask": 63,
                "login_shell": "/bin/zsh",
                "non_login": False,
                "root_prohibited": True,
                "principal_entity_id": "d4df7b8d-69c5-4ed6-9990-2e6e4f6029e8",
                "principal_resolution_digest": {
                    "algorithm": "sha256",
                    "value": "e" * 64,
                },
            },
            "worker_runtime": {"worker_version": "u10-worker/v1"},
        },
    }


def _outcome(*, run_id: str, worker_directory: Path, pid: int) -> dict:
    return {
        "schema_version": "semantic-guard-u10-worker-outcome/v1",
        "worker_version": "u10-worker/v1",
        "run_id": run_id,
        "entry_id": "entry.u10.test",
        "command_id": "verify.u10.test",
        "request_nonce": "a" * 64,
        "worker_identity": {
            "uid": 501,
            "gid": 20,
            "supplementary_gids": [],
            "umask": 63,
        },
        "launch_observation": {
            "pid": pid,
            "parent_pid": os.getpid(),
            "process_group_id": pid,
            "session_id": pid,
        },
        "receipt_locator": str(worker_directory / "receipt.json"),
        "receipt_artifact_digest": {"algorithm": "sha256", "value": "b" * 64},
        "receipt_semantic_digest": {"algorithm": "sha256", "value": "c" * 64},
        "execution_nonce": "d" * 64,
        "execution_status": "successful",
        "started_at": "2026-07-20T00:00:00Z",
        "finished_at": "2026-07-20T00:00:01Z",
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }


def _broker_process(pid: int) -> dict:
    return {
        "pid": pid,
        "parent_pid": os.getpid(),
        "process_group_id": pid,
        "session_id": pid,
        "observed_at": "2026-07-19T23:59:59Z",
    }


class U10SupervisorProcessBindingTests(unittest.TestCase):
    def test_account_groups_cannot_substitute_for_effective_groups(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            worker_directory = Path(temporary)
            run_id = "run.u10.group-substitution"
            outcome = _outcome(
                run_id=run_id,
                worker_directory=worker_directory,
                pid=40001,
            )
            outcome["worker_identity"]["supplementary_gids"] = [12, 61]
            with self.assertRaises(BrokerBoundaryError) as observed:
                _validate_worker_outcome(
                    outcome,
                    context=_context(),
                    run_id=run_id,
                    worker_directory=worker_directory,
                    broker_process_observation=_broker_process(40001),
                )
            self.assertEqual(
                observed.exception.code,
                "u10_worker_outcome_binding_mismatch",
            )

    def test_root_observed_pid_must_match_worker_self_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            worker_directory = Path(temporary)
            run_id = "run.u10.pid-mismatch"
            with patch(
                "semantic_guard_u10_broker.supervisor.read_protected_file"
            ) as protected_read:
                with self.assertRaises(BrokerBoundaryError) as observed:
                    _validate_worker_outcome(
                        _outcome(
                            run_id=run_id,
                            worker_directory=worker_directory,
                            pid=41002,
                        ),
                        context=_context(),
                        run_id=run_id,
                        worker_directory=worker_directory,
                        broker_process_observation=_broker_process(41001),
                    )
            self.assertEqual(
                observed.exception.code,
                "u10_worker_launch_observation_mismatch",
            )
            protected_read.assert_not_called()

    def test_matching_root_observed_pid_reaches_receipt_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            worker_directory = Path(temporary)
            run_id = "run.u10.pid-match"
            root_observed_pid = 42001
            with patch(
                "semantic_guard_u10_broker.supervisor.read_protected_file",
                side_effect=BrokerBoundaryError("sentinel_receipt_read", run_id),
            ) as protected_read:
                with self.assertRaises(BrokerBoundaryError) as observed:
                    _validate_worker_outcome(
                        _outcome(
                            run_id=run_id,
                            worker_directory=worker_directory,
                            pid=root_observed_pid,
                        ),
                        context=_context(),
                        run_id=run_id,
                        worker_directory=worker_directory,
                        broker_process_observation=_broker_process(
                            root_observed_pid
                        ),
                    )
            self.assertEqual(observed.exception.code, "sentinel_receipt_read")
            protected_read.assert_called_once_with(
                worker_directory / "receipt.json",
                protected_root=worker_directory,
            )

    def test_worker_pid_pgid_and_sid_must_match_root_observation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            worker_directory = Path(temporary)
            run_id = "run.u10.process-mismatch"
            for field in ("pid", "process_group_id", "session_id"):
                outcome = _outcome(
                    run_id=run_id,
                    worker_directory=worker_directory,
                    pid=43001,
                )
                outcome["launch_observation"][field] += 1
                with self.subTest(field=field), self.assertRaises(
                    BrokerBoundaryError
                ) as observed:
                    _validate_worker_outcome(
                        outcome,
                        context=_context(),
                        run_id=run_id,
                        worker_directory=worker_directory,
                        broker_process_observation=_broker_process(43001),
                    )
                self.assertEqual(
                    observed.exception.code,
                    "u10_worker_launch_observation_mismatch",
                )

    def test_worker_self_report_without_root_observation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            worker_directory = Path(temporary)
            run_id = "run.u10.self-report-only"
            with self.assertRaises(BrokerBoundaryError) as observed:
                _validate_worker_outcome(
                    _outcome(
                        run_id=run_id,
                        worker_directory=worker_directory,
                        pid=44001,
                    ),
                    context=_context(),
                    run_id=run_id,
                    worker_directory=worker_directory,
                    broker_process_observation={},
                )
            self.assertEqual(
                observed.exception.code,
                "u10_broker_process_observation_invalid",
            )

    def test_root_records_popen_pid_parent_pgid_sid_and_time(self) -> None:
        process = Mock(pid=45001)
        with (
            patch(
                "semantic_guard_u10_broker.supervisor.os.getpgid",
                return_value=45001,
            ) as getpgid,
            patch(
                "semantic_guard_u10_broker.supervisor.os.getsid",
                return_value=45001,
            ) as getsid,
            patch(
                "semantic_guard_u10_broker.supervisor._utc_now",
                return_value="2026-07-20T00:00:00Z",
            ),
        ):
            observed = _observe_launched_worker_process(process)
        self.assertEqual(
            observed,
            {
                "pid": 45001,
                "parent_pid": os.getpid(),
                "process_group_id": 45001,
                "session_id": 45001,
                "observed_at": "2026-07-20T00:00:00Z",
            },
        )
        getpgid.assert_called_once_with(45001)
        getsid.assert_called_once_with(45001)

    def test_quiescence_observation_is_root_timestamp(self) -> None:
        with (
            patch(
                "semantic_guard_u10_broker.supervisor.os.killpg",
                side_effect=ProcessLookupError,
            ),
            patch(
                "semantic_guard_u10_broker.supervisor._utc_now",
                return_value="2026-07-20T00:00:02Z",
            ),
        ):
            self.assertEqual(
                _ensure_worker_process_group_quiescent(46001),
                "2026-07-20T00:00:02Z",
            )

    def test_exclusive_write_establishes_exact_mode_despite_parent_umask(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "broker-context.json"
            previous_umask = os.umask(0o077)
            try:
                _write_exclusive(path, b"trusted-context\n", mode=0o640)
            finally:
                os.umask(previous_umask)

            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)
            self.assertEqual(path.read_bytes(), b"trusted-context\n")


if __name__ == "__main__":
    unittest.main()
