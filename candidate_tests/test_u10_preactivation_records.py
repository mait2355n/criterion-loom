from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import pwd
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from jsonschema import Draft202012Validator


SCRIPTS = Path(__file__).parent / "fixtures" / "scripts"
CANDIDATE_PATH = SCRIPTS / "prepare_u10_root_candidate.py"
TOOL_PATH = SCRIPTS / "prepare_u10_preactivation_records.py"
SCHEMAS = Path(__file__).parents[1] / "src" / "semantic_guard_vnext" / "validation" / "env-path-contracts"

CANDIDATE_SPEC = importlib.util.spec_from_file_location(
    "prepare_u10_root_candidate", CANDIDATE_PATH
)
assert CANDIDATE_SPEC is not None and CANDIDATE_SPEC.loader is not None
CANDIDATE = importlib.util.module_from_spec(CANDIDATE_SPEC)
sys.modules["prepare_u10_root_candidate"] = CANDIDATE
CANDIDATE_SPEC.loader.exec_module(CANDIDATE)

TOOL_SPEC = importlib.util.spec_from_file_location(
    "prepare_u10_preactivation_records", TOOL_PATH
)
assert TOOL_SPEC is not None and TOOL_SPEC.loader is not None
TOOL = importlib.util.module_from_spec(TOOL_SPEC)
TOOL_SPEC.loader.exec_module(TOOL)


class U10PreactivationRecordToolTests(unittest.TestCase):
    def setUp(self) -> None:
        # Exercise the fixed 501:20 policy without requiring that account on
        # the CI host. Unknown account lookups still fail as the OS would.
        self.worker_account = pwd.struct_passwd(
            ("u10-fixture-worker", "x", 501, 20, "", "/fixture/u10-worker", "/bin/sh")
        )
        account_database = SimpleNamespace(
            getpwnam=self._getpwnam, getpwuid=self._getpwuid
        )
        self.enterContext(mock.patch.object(CANDIDATE, "pwd", account_database))
        self.enterContext(mock.patch.object(TOOL, "pwd", account_database))
        self.enterContext(
            mock.patch.object(CANDIDATE.os, "getgrouplist", self._getgrouplist)
        )

    def _getpwnam(self, name: str) -> pwd.struct_passwd:
        if name != self.worker_account.pw_name:
            raise KeyError(name)
        return self.worker_account

    def _getpwuid(self, uid: int) -> pwd.struct_passwd:
        if uid != self.worker_account.pw_uid:
            raise KeyError(uid)
        return self.worker_account

    def _getgrouplist(self, name: str, gid: int) -> list[int]:
        account = self._getpwnam(name)
        if gid != account.pw_gid:
            raise KeyError((name, gid))
        return [account.pw_gid, 80]

    def _decision(
        self,
        root: Path,
        *,
        threat: str = "local_bounded_repository_suite_only",
        worker: str | None = "current_user_501_20_empty_supplementary_groups",
        human_decision: str = "accept",
    ) -> Path:
        evidence = root / "decision-evidence.json"
        evidence.write_text('{"human":"test-only"}\n', encoding="utf-8")
        entrypoint = root / "trusted-entrypoint.txt"
        entrypoint.write_text("test-only entrypoint\n", encoding="utf-8")
        decision = {
            "schema_version": "semantic-guard-u10-preactivation-decision/v1",
            "decision_id": "decision.u10.records-tool.test",
            "decision_version": "1.0.0-test",
            "record_kind": "u10_preactivation_scope_decision",
            "notation_profile": "entity-reference-notation/v0",
            "decision_entity_ref": "records tool test decision・6a3207ac-4067-4455-8633-366a6a4ea660",
            "subject_entity_ref": f"U-10 subject・{CANDIDATE.U10_SUBJECT_ENTITY_ID}",
            "human_decision": human_decision,
            "decision_owner": "human",
            "threat_boundary_selection": threat,
            "worker_identity_selection": worker,
            "decision_evidence_ref": {
                "record_id": "evidence.u10.records-tool.test",
                "locator": str(evidence.resolve()),
                "content_digest": CANDIDATE.digest_bytes(evidence.read_bytes()),
                "trust_domain": "test-only",
            },
            "trusted_entrypoint_ref": {
                "record_id": "entrypoint.u10.records-tool.test",
                "locator": str(entrypoint.resolve()),
                "content_digest": CANDIDATE.digest_bytes(entrypoint.read_bytes()),
            },
            "recorded_at": "2026-01-01T00:00:00Z",
            "requalification_triggers": [
                "threat_boundary_change",
                "worker_identity_policy_change",
                "principal_resolution_change",
                "host_or_os_change",
                "sandbox_or_external_executor_change",
                "qualified_test_denominator_change",
            ],
            "u4_principal_authenticity": "unresolved",
            "authority_scope": "u10_preactivation_scope_selection_only",
            "formal_authority": "human_scope_selection_only",
            "positive_assurance_allowed": False,
        }
        decision["decision_digest"] = CANDIDATE.sealed_digest(
            decision, "decision_digest"
        )
        path = root / "decision.json"
        path.write_bytes(CANDIDATE.canonical_json_bytes(decision) + b"\n")
        return path

    def _schema(self, name: str) -> dict:
        return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))

    def test_observe_then_resolve_records_selected_account_and_no_human_decision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            decision = self._decision(root)
            observation_path = root / "observation.json"
            resolution_path = root / "resolution.json"
            observed = TOOL.observe(
                decision_path=decision,
                output=observation_path,
                account_name=None,
            )
            resolved = TOOL.resolve(
                decision_path=decision,
                observation_path=observation_path,
                output=resolution_path,
            )
            observation = json.loads(observation_path.read_text(encoding="utf-8"))
            resolution = json.loads(resolution_path.read_text(encoding="utf-8"))
            Draft202012Validator(
                self._schema("u10-preactivation-decision-v1.schema.json"),
                format_checker=Draft202012Validator.FORMAT_CHECKER,
            ).validate(json.loads(decision.read_text(encoding="utf-8")))
            Draft202012Validator(
                self._schema("u10-worker-account-observation-v1.schema.json"),
                format_checker=Draft202012Validator.FORMAT_CHECKER,
            ).validate(observation)
            Draft202012Validator(
                self._schema("u10-worker-principal-resolution-v1.schema.json"),
                format_checker=Draft202012Validator.FORMAT_CHECKER,
            ).validate(resolution)
            self.assertEqual(observation["uid"], 501)
            self.assertEqual(observation["gid"], 20)
            self.assertEqual(observation["account_supplementary_gids"], [80])
            self.assertIsInstance(observation["account_supplementary_gids"], list)
            self.assertEqual(resolution["effective_supplementary_gids"], [])
            self.assertEqual(
                resolution["account_supplementary_gids"],
                observation["account_supplementary_gids"],
            )
            self.assertFalse(observed["human_decision_created"])
            self.assertFalse(resolved["human_decision_created"])
            self.assertEqual(observed["formal_authority"], "none")
            self.assertEqual(resolved["formal_authority"], "none")

    def test_observe_refuses_hostile_and_deferred_decisions(self) -> None:
        for threat, worker, human in (
            (
                "hostile_code_in_scope_requires_external_executor",
                None,
                "accept",
            ),
            ("defer", None, "defer"),
        ):
            with self.subTest(threat=threat), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                decision = self._decision(
                    root, threat=threat, worker=worker, human_decision=human
                )
                with self.assertRaises(CANDIDATE.CandidateBoundaryError) as observed:
                    TOOL.observe(
                        decision_path=decision,
                        output=root / "observation.json",
                        account_name=None,
                    )
                self.assertEqual(
                    observed.exception.code,
                    "preactivation_worker_observation_not_applicable",
                )

    def test_resolution_rejects_decision_locator_substitution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            decision = self._decision(root)
            observation = root / "observation.json"
            TOOL.observe(
                decision_path=decision,
                output=observation,
                account_name=None,
            )
            substituted = root / "substituted-decision.json"
            substituted.write_bytes(decision.read_bytes())
            with self.assertRaises(CANDIDATE.CandidateBoundaryError) as observed:
                TOOL.resolve(
                    decision_path=substituted,
                    observation_path=observation,
                    output=root / "resolution.json",
                )
            self.assertEqual(
                observed.exception.code,
                "candidate_worker_account_observation_invalid",
            )

    def test_output_is_exclusive_and_cli_has_no_decision_creation_command(self) -> None:
        parser = TOOL._parser()
        self.assertEqual(
            parser.parse_args(
                ["observe", "--decision", "/d", "--output", "/o"]
            ).command,
            "observe",
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            decision = self._decision(root)
            output = root / "observation.json"
            TOOL.observe(
                decision_path=decision, output=output, account_name=None
            )
            with self.assertRaises(CANDIDATE.CandidateBoundaryError):
                TOOL.observe(
                    decision_path=decision, output=output, account_name=None
                )


if __name__ == "__main__":
    unittest.main()
