"""Reviewer child-process mechanics exercised against fake executables."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from workflow_tests.agent_fakes import ANSWER_VALID_REVIEW, POSIX, path_with, write_fake_agent

_DRIVER = """
import json
from semantic_guard_workflow import mcp_server

result = mcp_server.llm_review_run_tool({"candidate": "ascii", "request": "ascii"}, execute=True)
print(json.dumps({key: result[key] for key in ("execution_status", "valid", "errors")}))
"""


@unittest.skipUnless(POSIX, "fake agents are /bin/sh wrappers")
class LocaleIndependenceTests(unittest.TestCase):
    def test_ascii_locale_does_not_break_a_utf8_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bin_dir = Path(directory)
            write_fake_agent(bin_dir, "codex", ANSWER_VALID_REVIEW)
            env = {
                **os.environ,
                "PATH": path_with(bin_dir),
                "LC_ALL": "C",
                "LANG": "C",
                "PYTHONCOERCECLOCALE": "0",
                "PYTHONUTF8": "0",
            }
            env.pop("PYTHONIOENCODING", None)

            completed = subprocess.run(
                [sys.executable, "-c", _DRIVER], env=env, capture_output=True, text=True, check=False
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["execution_status"], "valid_review")


if __name__ == "__main__":
    unittest.main()
