"""Digest-bound, site-free bootstrap for the U-10 unittest runner.

This file is intentionally self-contained.  It is launched only as

    python.vnext -I -S /absolute/path/to/this-file ...

so neither sitecustomize nor .pth files execute before the macOS sandbox has
prohibited process creation. Dependency import roots and exact test-source
files are handled only after containment is active. Test files are compiled
from verified bytes; the repository package initializer and broad subject
import roots are never used.
"""

from __future__ import annotations

import errno
import os
import sys


RUNNER_VERSION = "1.4.0"
TRACE_PROTOCOL = "semantic-guard-process-containment-trace/v1"
CONTAINMENT_PROTOCOL = "macos-sandbox-no-process-creation/v1"
TRACE_FD_ENV = "SEMANTIC_GUARD_TRACE_FD"
EXECUTION_NONCE_ENV = "SEMANTIC_GUARD_EXECUTION_NONCE"
COMMAND_DIGEST_ENV = "SEMANTIC_GUARD_COMMAND_DIGEST"
SUBJECT_MANIFEST_DIGEST_ENV = "SEMANTIC_GUARD_SUBJECT_MANIFEST_DIGEST"


def _trace_fd() -> int:
    raw = os.environ.get(TRACE_FD_ENV)
    try:
        descriptor = int(raw) if raw is not None else -1
        if descriptor <= 2:
            raise ValueError
        os.fstat(descriptor)
    except (OSError, TypeError, ValueError) as exc:
        raise RuntimeError("containment trace descriptor is missing or invalid") from exc
    return descriptor


def _raw_trace(descriptor: int, encoded_record: bytes) -> None:
    os.write(descriptor, encoded_record + b"\n")


def _fixed_hex_binding(name: str) -> str:
    value = os.environ.get(name, "")
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise RuntimeError(f"missing or invalid execution binding: {name}")
    return value


def _verify_outer_macos_sandbox(descriptor: int) -> None:
    execution_nonce = _fixed_hex_binding(EXECUTION_NONCE_ENV)
    command_digest = _fixed_hex_binding(COMMAND_DIGEST_ENV)
    subject_manifest_digest = _fixed_hex_binding(SUBJECT_MANIFEST_DIGEST_ENV)
    if sys.platform != "darwin":
        _raw_trace(
            descriptor,
            b'{"event":"containment_activation_failed","reason_code":"unsupported_platform","sequence":1,"trace_protocol":"semantic-guard-process-containment-trace/v1"}',
        )
        raise RuntimeError("the qualified containment profile is macOS-only")
    checks: dict[str, int | None] = {}
    if not hasattr(os, "fork"):
        _raw_trace(
            descriptor,
            b'{"event":"containment_activation_failed","reason_code":"fork_probe_unavailable","sequence":1,"trace_protocol":"semantic-guard-process-containment-trace/v1"}',
        )
        raise RuntimeError("fork probe is unavailable")
    try:
        pid = os.fork()
    except OSError as exc:
        checks["fork"] = exc.errno
    else:  # pragma: no cover - hostile outer-containment failure path.
        if pid == 0:
            os._exit(72)
        os.waitpid(pid, 0)
        checks["fork"] = None
    try:
        os.execve("/usr/bin/true", ["true"], {"PATH": ""})
    except OSError as exc:
        checks["exec_other"] = exc.errno
    denied = all(value in {errno.EPERM, errno.EACCES} for value in checks.values())
    if not denied:
        _raw_trace(
            descriptor,
            b'{"event":"containment_activation_failed","reason_code":"outer_policy_not_effective","sequence":1,"trace_protocol":"semantic-guard-process-containment-trace/v1"}',
        )
        raise RuntimeError(f"outer macOS containment is ineffective: {checks!r}")
    _raw_trace(
        descriptor,
        (
            '{"command_digest":"%s","event":"containment_activated",'
            '"execution_nonce":"%s","outer_probe":"fork_and_non_python_exec_denied",'
            '"process_creation_policy":"prohibited_after_runner_start",'
            '"protocol":"macos-sandbox-no-process-creation/v1","sequence":1,'
            '"subject_manifest_digest":"%s",'
            '"trace_protocol":"semantic-guard-process-containment-trace/v1"}'
            % (command_digest, execution_nonce, subject_manifest_digest)
        ).encode("ascii"),
    )


# Nothing supplied by site-packages, .pth files, or the subject has executed
# before this point.
_TRACE_DESCRIPTOR = _trace_fd()
_verify_outer_macos_sandbox(_TRACE_DESCRIPTOR)


import argparse  # noqa: E402  (imports deliberately happen after containment)
import hashlib  # noqa: E402
import json  # noqa: E402
import stat  # noqa: E402
import subprocess  # noqa: E402
import types  # noqa: E402
import unittest  # noqa: E402
from typing import Any  # noqa: E402


_PROCESS_AUDIT_EVENTS = frozenset(
    {
        "os.exec",
        "os.fork",
        "os.forkpty",
        "os.posix_spawn",
        "os.spawn",
        "os.system",
        "subprocess.Popen",
    }
)


class _Trace:
    def __init__(self, descriptor: int) -> None:
        self._fd = descriptor
        self._bindings = {
            "execution_nonce": _fixed_hex_binding(EXECUTION_NONCE_ENV),
            "command_digest": _fixed_hex_binding(COMMAND_DIGEST_ENV),
            "subject_manifest_digest": _fixed_hex_binding(
                SUBJECT_MANIFEST_DIGEST_ENV
            ),
        }
        self.sequence = 1  # activation is the first, raw bootstrap event
        self.process_creation_attempt_count = 0
        self._emitting = False

    def emit(self, event: str, **payload: Any) -> None:
        if self._emitting:
            return
        self._emitting = True
        try:
            self.sequence += 1
            record = {
                "trace_protocol": TRACE_PROTOCOL,
                "sequence": self.sequence,
                "event": event,
                **self._bindings,
                **payload,
            }
            _raw_trace(
                self._fd,
                json.dumps(
                    record,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8"),
            )
        finally:
            self._emitting = False

    def audit(self, event: str, _arguments: tuple[Any, ...]) -> None:
        if event in _PROCESS_AUDIT_EVENTS or event.startswith("os.exec") or event.startswith("os.spawn"):
            self.process_creation_attempt_count += 1
            self.emit(
                "process_creation_attempt",
                audit_event=event,
                attempt_number=self.process_creation_attempt_count,
            )

    def record_unobserved_api_attempt(self, event: str) -> None:
        """Record a denied API call when CPython emits no audit event for it.

        Some macOS/Python combinations reject ``subprocess`` in the launcher
        before the documented ``subprocess.Popen`` hook is observed.  The
        explicit API call is still an attempted process creation and must not
        disappear from the closed containment evidence.
        """

        self.process_creation_attempt_count += 1
        self.emit(
            "process_creation_attempt",
            audit_event=f"explicit_api:{event}",
            attempt_number=self.process_creation_attempt_count,
        )


def _absolute_directory(value: str) -> str:
    normalized = os.path.realpath(value)
    if not os.path.isabs(value) or not os.path.isdir(normalized):
        raise RuntimeError(f"approved import root is not an absolute directory: {value}")
    return normalized


def _install_dependency_roots(dependency_roots: list[str]) -> None:
    roots = [_absolute_directory(item) for item in dependency_roots]
    # Do not invoke site.addsitedir: that would execute .pth directives.  The
    # exact directories are sufficient for ordinary wheels.
    for root in reversed(roots):
        if root not in sys.path:
            sys.path.insert(0, root)


def _probe_enforcement(trace: _Trace) -> bool:
    results: dict[str, str] = {}
    subprocess_attempts_before = trace.process_creation_attempt_count
    try:
        completed = subprocess.run(
            ["/usr/bin/true"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            env={"PATH": ""},
        )
        results["subprocess"] = f"unexpected_exit_{completed.returncode}"
    except OSError as exc:
        results["subprocess"] = f"denied_errno_{exc.errno}"
    if trace.process_creation_attempt_count == subprocess_attempts_before:
        trace.record_unobserved_api_attempt("subprocess.run")
    if hasattr(os, "fork"):
        fork_attempts_before = trace.process_creation_attempt_count
        try:
            pid = os.fork()
        except OSError as exc:
            results["fork"] = f"denied_errno_{exc.errno}"
        else:  # pragma: no cover - hostile containment-failure path.
            if pid == 0:
                os._exit(73)
            os.waitpid(pid, 0)
            results["fork"] = "unexpected_succeeded"
        if trace.process_creation_attempt_count == fork_attempts_before:
            trace.record_unobserved_api_attempt("os.fork")
    denied_values = {f"denied_errno_{errno.EPERM}", f"denied_errno_{errno.EACCES}"}
    denied = bool(results) and all(value in denied_values for value in results.values())
    trace.emit(
        "containment_probe_completed",
        enforcement_status="effective" if denied else "ineffective",
        api_results=results,
        process_creation_attempt_count=trace.process_creation_attempt_count,
        executed_child_count=0 if denied else 1,
    )
    return denied


def _loaded_test_ids(suite: unittest.TestSuite) -> list[str]:
    identifiers: list[str] = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            identifiers.extend(_loaded_test_ids(item))
        else:
            identifiers.append(str(item.id()))
    return identifiers


def _module_name(value: str) -> str:
    if not value or any(not part.isidentifier() for part in value.split(".")):
        raise RuntimeError(f"invalid isolated test module name: {value!r}")
    return value


def _test_source_bindings(
    source_files: list[str], source_digests: list[str], module_names: list[str]
) -> list[dict[str, str]]:
    if not source_files or not (
        len(source_files) == len(source_digests) == len(module_names)
    ):
        raise RuntimeError("exact test-source binding cardinality mismatch")
    bindings: list[dict[str, str]] = []
    for source_file, source_digest, module_name in zip(
        source_files, source_digests, module_names, strict=True
    ):
        if len(source_digest) != 64 or any(
            character not in "0123456789abcdef" for character in source_digest
        ):
            raise RuntimeError("invalid test-source SHA-256 digest")
        if not os.path.isabs(source_file):
            raise RuntimeError(f"test source is not absolute: {source_file}")
        resolved = os.path.realpath(source_file)
        if source_file != resolved:
            raise RuntimeError(
                f"test source must already be an exact resolved path: {source_file}"
            )
        bindings.append(
            {
                "module_name": _module_name(module_name),
                "source_file": resolved,
                "source_digest": source_digest,
            }
        )
    binding_keys = {
        (item["module_name"], item["source_file"], item["source_digest"])
        for item in bindings
    }
    if len(binding_keys) != len(bindings):
        raise RuntimeError("duplicate exact test-source binding")
    if len({item["module_name"] for item in bindings}) != len(bindings):
        raise RuntimeError("duplicate isolated test module name")
    if len({item["source_file"] for item in bindings}) != len(bindings):
        raise RuntimeError("duplicate exact test-source file")
    return bindings


def _read_verified_source(
    binding: dict[str, str],
) -> tuple[bytes, dict[str, int | str]]:
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(binding["source_file"], flags)
    except OSError as exc:
        raise RuntimeError(
            f"cannot open exact test source: {binding['source_file']}"
        ) from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise RuntimeError(
                f"exact test source is not a regular file: {binding['source_file']}"
            )
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    stable_identity = (
        before.st_dev == after.st_dev
        and before.st_ino == after.st_ino
        and before.st_size == after.st_size
        and before.st_mtime_ns == after.st_mtime_ns
        and before.st_ctime_ns == after.st_ctime_ns
    )
    if not stable_identity:
        raise RuntimeError(
            f"exact test source changed while being read: {binding['source_file']}"
        )
    source = b"".join(chunks)
    observed_digest = hashlib.sha256(source).hexdigest()
    if observed_digest != binding["source_digest"]:
        raise RuntimeError(
            f"exact test-source digest mismatch: {binding['source_file']}"
        )
    return source, {
        "device": before.st_dev,
        "inode": before.st_ino,
        "size": len(source),
        "observed_digest": observed_digest,
    }


def _load_isolated_test_module(
    binding: dict[str, str], source: bytes
) -> types.ModuleType:
    module = types.ModuleType(binding["module_name"])
    module.__file__ = binding["source_file"]
    module.__loader__ = None
    module.__package__ = ""
    module.__spec__ = None
    code = compile(source, binding["source_file"], "exec", dont_inherit=True)
    exec(code, module.__dict__)
    return module


def _run_tests(
    trace: _Trace,
    source_bindings: list[dict[str, str]],
    expected_test_ids: list[str],
) -> int:
    trace.emit(
        "test_loading_started",
        test_source_bindings=source_bindings,
        expected_test_ids=expected_test_ids,
    )
    suite = unittest.TestSuite()
    for binding in source_bindings:
        try:
            source, observation = _read_verified_source(binding)
            module = _load_isolated_test_module(binding, source)
        except (OSError, RuntimeError, SyntaxError, UnicodeError) as exc:
            trace.emit(
                "test_source_rejected",
                test_source_binding=binding,
                reason_code="exact_test_source_load_failed",
                error_type=type(exc).__name__,
            )
            return 78
        trace.emit(
            "test_source_verified",
            test_source_binding=binding,
            source_observation=observation,
        )
        suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
    loaded_test_ids = _loaded_test_ids(suite)
    if (
        not expected_test_ids
        or len(expected_test_ids) != len(set(expected_test_ids))
        or len(loaded_test_ids) != len(set(loaded_test_ids))
        or loaded_test_ids != expected_test_ids
    ):
        trace.emit(
            "test_denominator_mismatch",
            test_source_bindings=source_bindings,
            expected_test_ids=expected_test_ids,
            loaded_test_ids=loaded_test_ids,
            reason_code="closed_test_denominator_mismatch",
        )
        return 78
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=2).run(suite)
    qualified_success = (
        result.wasSuccessful()
        and result.testsRun == len(expected_test_ids)
        and result.testsRun > 0
        and len(result.skipped) == 0
    )
    trace.emit(
        "test_run_completed",
        successful=qualified_success,
        tests_run=result.testsRun,
        failures=len(result.failures),
        errors=len(result.errors),
        skipped=len(result.skipped),
        test_ids=loaded_test_ids,
        process_creation_attempt_count=trace.process_creation_attempt_count,
        executed_child_count=0,
    )
    return 0 if qualified_success else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="semantic-guard-governed-test-runner")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--probe-containment", action="store_true")
    parser.add_argument("--dependency-import-root", action="append", default=[])
    parser.add_argument("--test-source-file", action="append", default=[])
    parser.add_argument("--test-source-digest", action="append", default=[])
    parser.add_argument("--test-module-name", action="append", default=[])
    parser.add_argument("--expected-test-id", action="append", default=[])
    arguments = parser.parse_args(argv)
    trace = _Trace(_TRACE_DESCRIPTOR)
    sys.addaudithook(trace.audit)
    try:
        source_bindings = _test_source_bindings(
            list(arguments.test_source_file),
            list(arguments.test_source_digest),
            list(arguments.test_module_name),
        )
    except RuntimeError as exc:
        source_bindings: list[dict[str, str]] = []
        source_binding_error = str(exc)
    else:
        source_binding_error = None
    trace.emit(
        "runner_started",
        protocol=CONTAINMENT_PROTOCOL,
        executable=sys.executable,
        no_site=bool(sys.flags.no_site),
        isolated=bool(sys.flags.isolated),
        test_source_bindings=source_bindings,
        expected_test_ids=list(arguments.expected_test_id),
        cwd=os.getcwd(),
        dependency_import_roots=list(arguments.dependency_import_root),
    )
    if not sys.flags.no_site or not sys.flags.isolated:
        trace.emit("runner_failed", reason_code="startup_isolation_flags_missing")
        return 76
    if arguments.version:
        print(RUNNER_VERSION)
        trace.emit("runner_version_reported", runner_version=RUNNER_VERSION, executed_child_count=0)
        return 0
    if arguments.probe_containment:
        return 0 if _probe_enforcement(trace) else 74
    if source_binding_error is not None:
        trace.emit(
            "runner_failed",
            reason_code="exact_test_source_binding_invalid",
            error=source_binding_error,
        )
        return 64
    _install_dependency_roots(list(arguments.dependency_import_root))
    return _run_tests(
        trace,
        source_bindings,
        list(arguments.expected_test_id),
    )


if __name__ == "__main__":
    raise SystemExit(main())
