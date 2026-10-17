"""Fake reviewer executables for tests that must run a real child process.

No real ``codex`` or ``claude`` is ever started: a test writes a small Python
script into a temporary directory and puts a ``/bin/sh`` wrapper named after
the agent first on ``PATH``.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

POSIX = os.name == "posix"

VALID_REVIEW: dict[str, Any] = {
    "schema_version": "candidate-gap-review/v2",
    "review_status": "no_supplement_needed",
    "missing_aspects": [],
    "questionable_assumptions": [],
    "possible_counter_conditions": [],
    "supplement_proposals": [],
    "rule_item_reviews": [],
    "human_decision_needed": [],
}

ANSWER_VALID_REVIEW = (
    "import json, sys\n"
    "sys.stdin.buffer.read()\n"
    f"sys.stdout.buffer.write(json.dumps({VALID_REVIEW!r}).encode())\n"
)


def write_fake_agent(directory: Path, name: str, source: str) -> Path:
    """Create ``directory/name`` that runs ``source`` with the current interpreter."""
    script = directory / f"{name}.py"
    script.write_text(source, encoding="utf-8")
    wrapper = directory / name
    wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8")
    wrapper.chmod(0o755)
    return wrapper


def path_with(directory: Path) -> str:
    return os.pathsep.join([str(directory), os.environ.get("PATH", "")])


def claude_envelope(structured_output: dict[str, Any] | None = None, **fields: Any) -> str:
    envelope: dict[str, Any] = {"type": "result", "subtype": "success", "is_error": False, "permission_denials": []}
    if structured_output is not None:
        envelope["structured_output"] = structured_output
    envelope.update(fields)
    return json.dumps(envelope, ensure_ascii=False)
