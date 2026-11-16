"""Bounded child-process execution for reviewer agents.

``subprocess.run`` is not enough for an agent CLI: its timeout kills only the
direct child (descendants keep running and keep billing), a finished child whose
descendant still holds the output pipe makes it wait out the whole timeout and
report a timeout, and it buffers output without limit. :func:`run_agent_process`
keeps the ``subprocess.run`` call shape the runtime uses, starts the agent in
its own process group, kills the whole group on timeout, stops waiting for a
pipe once the direct child has finished, and caps the captured output.
"""

from __future__ import annotations

import os
import signal
import subprocess
import threading
from collections.abc import Sequence
from pathlib import Path
from typing import Any

MAX_OUTPUT_BYTES = 4 * 1024 * 1024

_DRAIN_SECONDS = 1.0
_REAP_SECONDS = 5.0
_READ_CHUNK_BYTES = 65536


class BoundedCompletedProcess(subprocess.CompletedProcess):
    """``CompletedProcess`` that also says whether captured output was cut."""

    def __init__(
        self,
        args: Sequence[str],
        returncode: int,
        stdout: str,
        stderr: str,
        *,
        stdout_truncated: bool = False,
        stderr_truncated: bool = False,
    ) -> None:
        super().__init__(args, returncode, stdout, stderr)
        self.stdout_truncated = stdout_truncated
        self.stderr_truncated = stderr_truncated


def truncation_marker(limit: int, discarded: int | None = None) -> str:
    detail = "" if discarded is None else f", {discarded} bytes discarded"
    return f"\n[output truncated: only the first {limit} bytes are kept{detail}]"


def cap_text(text: str, limit: int = MAX_OUTPUT_BYTES) -> tuple[str, bool]:
    """Bound output from a runner that did not bound it (limit counted in characters)."""
    if len(text) <= limit:
        return text, False
    return text[:limit] + truncation_marker(limit), True


def run_agent_process(
    command: Sequence[str],
    *,
    input: str | None = None,
    timeout: float | None = None,
    cwd: str | Path | None = None,
    encoding: str = "utf-8",
    errors: str = "replace",
    max_output_bytes: int = MAX_OUTPUT_BYTES,
    **_subprocess_run_options: Any,
) -> BoundedCompletedProcess:
    """Run ``command`` like ``subprocess.run(text=True, capture_output=True, check=False)``.

    Raises :class:`subprocess.TimeoutExpired` (after killing the process group,
    with the partial output attached) and ``OSError``/``ValueError`` when the
    process cannot be started. The other ``subprocess.run`` options the runtime
    passes (``text``, ``capture_output``, ``check``) are fixed here.
    """
    popen_options: dict[str, Any] = {}
    if os.name == "posix":
        popen_options["start_new_session"] = True
    else:
        popen_options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=None if cwd is None else str(cwd),
        **popen_options,
    )
    assert process.stdin is not None and process.stdout is not None and process.stderr is not None
    data = (input or "").encode(encoding, errors)
    writer = threading.Thread(target=_feed, args=(process.stdin, data), daemon=True)
    stdout = _Capture(process.stdout, max_output_bytes)
    stderr = _Capture(process.stderr, max_output_bytes)
    readers = (stdout, stderr)
    for thread in (writer, *readers):
        thread.start()
    try:
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            _kill_process_tree(process)
            _drain(readers)
            raise subprocess.TimeoutExpired(
                list(command),
                timeout if timeout is not None else 0,
                output=stdout.text(encoding, errors),
                stderr=stderr.text(encoding, errors),
            ) from None
        # The direct child is done. A descendant that still holds a pipe is left
        # over from the reviewer, not part of its answer: stop it and keep what was read.
        if not _drain(readers):
            _kill_process_tree(process)
            _drain(readers)
    finally:
        if process.poll() is None:
            _kill_process_tree(process)
        writer.join(_DRAIN_SECONDS)
    return BoundedCompletedProcess(
        list(command),
        returncode,
        stdout.text(encoding, errors),
        stderr.text(encoding, errors),
        stdout_truncated=stdout.discarded > 0,
        stderr_truncated=stderr.discarded > 0,
    )


class _Capture(threading.Thread):
    def __init__(self, stream: Any, limit: int) -> None:
        super().__init__(daemon=True)
        self._stream = stream
        self._limit = limit
        self._chunks: list[bytes] = []
        self._lock = threading.Lock()
        self._kept = 0
        self.discarded = 0

    def run(self) -> None:
        try:
            while chunk := self._stream.read1(_READ_CHUNK_BYTES):
                with self._lock:
                    room = max(self._limit - self._kept, 0)
                    kept = chunk[:room]
                    if kept:
                        self._chunks.append(kept)
                        self._kept += len(kept)
                    self.discarded += len(chunk) - len(kept)
        except (OSError, ValueError):
            pass
        finally:
            try:
                self._stream.close()
            except (OSError, ValueError):
                pass

    def text(self, encoding: str, errors: str) -> str:
        with self._lock:
            text = b"".join(self._chunks).decode(encoding, errors)
            discarded = self.discarded
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        if discarded:
            text += truncation_marker(self._limit, discarded)
        return text


def _feed(stream: Any, data: bytes) -> None:
    try:
        stream.write(data)
        stream.flush()
    except (OSError, ValueError):
        pass  # the child stopped reading (or exited) before the prompt was delivered
    finally:
        try:
            stream.close()
        except (OSError, ValueError):
            pass


def _drain(readers: Sequence[threading.Thread]) -> bool:
    """Give the pipe readers a moment to reach end of file; False if one is still open."""
    for reader in readers:
        reader.join(_DRAIN_SECONDS)
    return not any(reader.is_alive() for reader in readers)


def _kill_process_tree(process: subprocess.Popen[bytes]) -> None:
    """Kill the agent and every descendant that is still in its process group."""
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)  # the agent is its own session and group leader
        except (ProcessLookupError, PermissionError):
            pass
    else:  # pragma: no cover - exercised on Windows only
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                capture_output=True,
                check=False,
                timeout=_REAP_SECONDS,
            )
        except (OSError, subprocess.SubprocessError):
            pass
    try:
        process.kill()
    except OSError:
        pass
    try:
        process.wait(timeout=_REAP_SECONDS)
    except subprocess.TimeoutExpired:
        pass
