#!/usr/bin/env python3
"""Fixed ID-only dispatcher for qualified U-10 control operations."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, Mapping

from semantic_guard_u10_broker import core
from semantic_guard_u10_broker.internal_contracts import (
    CONTROL_ALLOWED_OPERATIONS_V1,
)
from semantic_guard_u10_broker.protected_io import (
    CONTROL_EFFECTIVE_PYTHON_PATH,
    CONTROL_RUNTIME_MANIFEST_PATH,
    INITIAL_TRUST_PROVISIONER_PATH,
    ROOT_CONTROL_DISPATCHER_PATH,
    SNAPSHOT_STORE_PRODUCER_PATH,
    U10_ROOT,
    read_protected_file,
    strict_json_loads,
)


ALLOWED_OPERATIONS = frozenset(CONTROL_ALLOWED_OPERATIONS_V1)
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,255}$")
EXPECTED_ENVIRONMENT_KEYS = {
    "LC_ALL",
    "PATH",
    "PYTHONDONTWRITEBYTECODE",
    "SEMANTIC_GUARD_U10_BOOTSTRAP_BINDING_DIGEST",
    "SEMANTIC_GUARD_U10_CONTROL_RUNTIME_MANIFEST_DIGEST",
    "SEMANTIC_GUARD_U10_CONTROL_VERIFIED",
}


class ControlDispatchError(RuntimeError):
    pass


def _load_json(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = strict_json_loads(raw)
    except (UnicodeError, ValueError) as exc:
        raise ControlDispatchError(f"{label} is unreadable") from exc
    if not isinstance(value, dict):
        raise ControlDispatchError(f"{label} is not an object")
    return value


def _one_line_path(path: Path) -> Path:
    raw = read_protected_file(path, protected_root=U10_ROOT)
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise ControlDispatchError("control Python path is not UTF-8") from exc
    if not text.endswith("\n") or text.count("\n") != 1 or "\x00" in text:
        raise ControlDispatchError("control Python path is not one sealed line")
    result = Path(text[:-1])
    if (
        not result.is_absolute()
        or result != Path(os.path.normpath(str(result)))
        or Path(os.path.realpath(result)) != result
    ):
        raise ControlDispatchError("control Python path is not canonical")
    return result


def _consume_os_injected_environment() -> None:
    value = os.environ.get("__CF_USER_TEXT_ENCODING")
    if value is None:
        return
    matched = re.fullmatch(
        r"0x([0-9A-Fa-f]+):0x[0-9A-Fa-f]+:0x[0-9A-Fa-f]+", value
    )
    if matched is None or int(matched.group(1), 16) != os.geteuid():
        raise ControlDispatchError("invalid Darwin environment injection")
    os.environ.pop("__CF_USER_TEXT_ENCODING", None)


def _validate_startup() -> None:
    if os.geteuid() != 0 or os.getegid() != 0:
        raise ControlDispatchError("control dispatcher requires euid/egid 0")
    if not (
        sys.flags.isolated
        and not sys.flags.no_site
        and sys.flags.dont_write_bytecode
        and sys.flags.safe_path
    ):
        raise ControlDispatchError("control dispatcher requires -I -B")
    if (
        Path(__file__).absolute() != ROOT_CONTROL_DISPATCHER_PATH
        or Path(__file__).is_symlink()
    ):
        raise ControlDispatchError("control dispatcher path is not fixed")
    _consume_os_injected_environment()
    if set(os.environ) != EXPECTED_ENVIRONMENT_KEYS:
        raise ControlDispatchError("control environment denominator mismatch")
    if (
        os.environ.get("PATH") != ""
        or os.environ.get("LC_ALL") != "C"
        or os.environ.get("PYTHONDONTWRITEBYTECODE") != "1"
        or os.environ.get("SEMANTIC_GUARD_U10_CONTROL_VERIFIED")
        != "fixed-control-outer-v1"
    ):
        raise ControlDispatchError("control environment value mismatch")
    for name in (
        "SEMANTIC_GUARD_U10_BOOTSTRAP_BINDING_DIGEST",
        "SEMANTIC_GUARD_U10_CONTROL_RUNTIME_MANIFEST_DIGEST",
    ):
        if re.fullmatch(r"[0-9a-f]{64}", os.environ.get(name, "")) is None:
            raise ControlDispatchError("control environment digest invalid")
    if Path(os.path.realpath(sys.executable)) != _one_line_path(
        CONTROL_EFFECTIVE_PYTHON_PATH
    ):
        raise ControlDispatchError("running control interpreter mismatch")
    manifest = _load_json(
        read_protected_file(CONTROL_RUNTIME_MANIFEST_PATH, protected_root=U10_ROOT),
        "control runtime manifest",
    )
    if (
        manifest.get("schema_version")
        != "semantic-guard-u10-control-runtime-manifest/v1"
        or manifest.get("manifest_digest", {}).get("value")
        != os.environ[
            "SEMANTIC_GUARD_U10_CONTROL_RUNTIME_MANIFEST_DIGEST"
        ]
        or manifest.get("effective_interpreter_locator")
        != str(Path(os.path.realpath(sys.executable)))
    ):
        raise ControlDispatchError("control runtime marker mismatch")
    runtime_root = Path(str(manifest.get("runtime_root", "")))
    allowed_external = {ROOT_CONTROL_DISPATCHER_PATH, INITIAL_TRUST_PROVISIONER_PATH}
    for name, module in sys.modules.items():
        origin = getattr(module, "__file__", None)
        if origin is None or name == "__main__":
            continue
        resolved = Path(os.path.realpath(origin))
        try:
            resolved.relative_to(runtime_root)
        except ValueError:
            if resolved not in allowed_external:
                raise ControlDispatchError(
                    f"control module escaped runtime: {name}: {resolved}"
                )


def _request(arguments: list[str]) -> tuple[str, str]:
    if len(arguments) != 2:
        raise ControlDispatchError("OPERATION IDENTIFIER required")
    operation, identifier = arguments
    if operation not in ALLOWED_OPERATIONS:
        raise ControlDispatchError("control operation is not allowed")
    if IDENTIFIER.fullmatch(identifier) is None:
        raise ControlDispatchError("control identifier is invalid")
    return operation, identifier


def _load_provisioner() -> Any:
    observed = INITIAL_TRUST_PROVISIONER_PATH.lstat()
    if (
        stat.S_ISLNK(observed.st_mode)
        or not stat.S_ISREG(observed.st_mode)
        or observed.st_uid != 0
        or observed.st_gid != 0
        or observed.st_nlink != 1
        or observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    ):
        raise ControlDispatchError("initial provisioner is untrusted")
    read_protected_file(INITIAL_TRUST_PROVISIONER_PATH, protected_root=U10_ROOT)
    specification = importlib.util.spec_from_file_location(
        "_u10_control_initial_provisioner", INITIAL_TRUST_PROVISIONER_PATH
    )
    if specification is None or specification.loader is None:
        raise ControlDispatchError("initial provisioner loader unavailable")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    try:
        specification.loader.exec_module(module)
    except Exception:
        sys.modules.pop(specification.name, None)
        raise
    return module


def _load_snapshot_producer(
    publisher_binding: Mapping[str, Any],
) -> Any:
    """Load only the fixed producer sealed into this invocation binding."""

    observed = SNAPSHOT_STORE_PRODUCER_PATH.lstat()
    if (
        stat.S_ISLNK(observed.st_mode)
        or not stat.S_ISREG(observed.st_mode)
        or observed.st_uid != 0
        or observed.st_gid != 0
        or observed.st_nlink != 1
        or observed.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    ):
        raise ControlDispatchError("snapshot producer is untrusted")
    raw = read_protected_file(
        SNAPSHOT_STORE_PRODUCER_PATH, protected_root=U10_ROOT
    )
    try:
        expected = publisher_binding["artifacts"][
            "snapshot_store_producer"
        ]["artifact_digest"]
    except (KeyError, TypeError) as exc:
        raise ControlDispatchError(
            "snapshot producer binding is absent"
        ) from exc
    if expected != core.digest_bytes(raw):
        raise ControlDispatchError("snapshot producer binding mismatch")
    specification = importlib.util.spec_from_file_location(
        "_u10_control_snapshot_store_producer",
        SNAPSHOT_STORE_PRODUCER_PATH,
    )
    if specification is None or specification.loader is None:
        raise ControlDispatchError("snapshot producer loader unavailable")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    try:
        specification.loader.exec_module(module)
    except Exception:
        sys.modules.pop(specification.name, None)
        raise
    if raw != read_protected_file(
        SNAPSHOT_STORE_PRODUCER_PATH, protected_root=U10_ROOT
    ):
        sys.modules.pop(specification.name, None)
        raise ControlDispatchError("snapshot producer changed during load")
    return module


def dispatch(operation: str, identifier: str) -> dict[str, Any]:
    provisioner = _load_provisioner()
    try:
        provenance = provisioner.validate_bootstrap_provenance_chain()
    except Exception as exc:
        raise ControlDispatchError(
            f"bootstrap provenance validation failed: {exc}"
        ) from exc
    binding_digest = provenance["binding"]["binding_digest"]["value"]
    if binding_digest != os.environ[
        "SEMANTIC_GUARD_U10_BOOTSTRAP_BINDING_DIGEST"
    ]:
        raise ControlDispatchError("bootstrap provenance marker mismatch")
    publisher_binding = core.build_current_publisher_contract_binding_v1(
        provenance
    )
    if operation == "activate-store":
        return core.publish_active_root_trust_store_by_id_v1(
            identifier, publisher_contract_binding=publisher_binding
        )
    if operation == "revoke-store":
        return core.publish_store_revocation_by_id_v1(
            identifier, publisher_contract_binding=publisher_binding
        )
    if operation == "key":
        try:
            return provisioner.execute_key_authorization(
                identifier,
                publisher_contract_binding=publisher_binding,
            )
        except Exception as exc:
            raise ControlDispatchError(f"key operation failed: {exc}") from exc
    if operation in {"project-snapshot", "activate-snapshot"}:
        try:
            producer = _load_snapshot_producer(publisher_binding)
            function = (
                producer.project_snapshot_by_authorization_id
                if operation == "project-snapshot"
                else producer.activate_snapshot_by_authorization_id
            )
            return function(
                identifier,
                publisher_contract_binding=publisher_binding,
            )
        except Exception as exc:
            raise ControlDispatchError(
                f"{operation} operation failed: {exc}"
            ) from exc
    raise ControlDispatchError("unreachable control operation")


def main(argv: list[str] | None = None) -> int:
    _validate_startup()
    operation, identifier = _request(
        list(sys.argv[1:] if argv is None else argv)
    )
    result = dispatch(operation, identifier)
    envelope = {
        "schema_version": "semantic-guard-u10-control-result/v1",
        "operation": operation,
        "identifier": identifier,
        "result": result,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    print(
        json.dumps(
            envelope,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ControlDispatchError, core.BrokerBoundaryError, OSError) as exc:
        print(f"U-10 root control failed: {exc}", file=sys.stderr)
        raise SystemExit(70)
