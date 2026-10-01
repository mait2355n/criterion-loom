#!/usr/bin/env python3
"""Build a closed U-10 bootstrap capsule and a reviewable one-shot directive.

The directive is text to paste into a privileged shell after human review.  It
must not itself be executed as a mutable shell file.  The OS-protected Python
loader opens the capsule once with ``O_NOFOLLOW``, compares the complete bytes
to the embedded SHA-256 value, extracts the provisioner bytes from that same
in-memory object, verifies their digest, and compiles those exact bytes.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shlex
import stat
import sys
from typing import Any


CAPSULE_SCHEMA = "semantic-guard-u10-initial-bootstrap-capsule/v1"
PROVISIONER_MEMBER = "bootstrap/u10_initial_trust_provisioner.py"
LOADER = r'''import base64,hashlib,json,math,os,stat,sys
p=sys.argv[1]; expected=sys.argv[2]; provisioner_expected=sys.argv[3]; authorization_id=sys.argv[4]
def strict_object(pairs):
 value={}
 for key,item in pairs:
  if key in value: raise json.JSONDecodeError("duplicate object key: %r"%(key,),key,0)
  value[key]=item
 return value
def reject_constant(value): raise json.JSONDecodeError("non-finite JSON number: "+value,value,0)
def strict_float(value):
 parsed=float(value)
 if not math.isfinite(parsed): raise json.JSONDecodeError("non-finite JSON number: "+value,value,0)
 return parsed
def strict_load(raw):
 try: return json.loads(raw,object_pairs_hook=strict_object,parse_constant=reject_constant,parse_float=strict_float)
 except (UnicodeDecodeError,json.JSONDecodeError,ValueError) as exc: raise SystemExit("strict JSON rejection: "+str(exc))
fd=os.open(p,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0))
try:
 b=os.fstat(fd)
 if not stat.S_ISREG(b.st_mode) or b.st_nlink!=1 or b.st_size<2 or b.st_size>536870912: raise SystemExit("capsule is not one bounded regular file")
 chunks=[]
 while True:
  x=os.read(fd,1048576)
  if not x: break
  chunks.append(x)
 a=os.fstat(fd)
 if (b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns,b.st_ctime_ns)!=(a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns): raise SystemExit("capsule changed during read")
finally: os.close(fd)
raw=b"".join(chunks)
if hashlib.sha256(raw).hexdigest()!=expected: raise SystemExit("capsule digest mismatch")
capsule=strict_load(raw)
if set(capsule)!={"schema_version","capsule_kind","invocation_id","members","formal_authority","positive_assurance_allowed"} or capsule["schema_version"]!="semantic-guard-u10-initial-bootstrap-capsule/v1" or capsule["invocation_id"]!=authorization_id or capsule["capsule_kind"] not in {"root_runtime_observation","bootstrap_publication"} or capsule["formal_authority"]!="none" or capsule["positive_assurance_allowed"] is not False: raise SystemExit("capsule contract mismatch")
members={}
if not isinstance(capsule["members"],list) or not 1<=len(capsule["members"])<=20000: raise SystemExit("capsule member count outside bound")
decoded_total=0
for m in capsule["members"]:
 if set(m)!={"name","encoding","content","artifact_digest"} or m["encoding"]!="base64" or m["name"] in members: raise SystemExit("capsule member contract mismatch")
 content=base64.b64decode(m["content"],validate=True)
 if len(content)>67108864: raise SystemExit("capsule member exceeds byte bound")
 decoded_total+=len(content)
 if decoded_total>402653184: raise SystemExit("capsule decoded denominator exceeds byte bound")
 digest={"algorithm":"sha256","value":hashlib.sha256(content).hexdigest()}
 if m["artifact_digest"]!=digest: raise SystemExit("capsule member digest mismatch")
 members[m["name"]]=(content,digest)
def seal(v,field):
 material=dict(v); material.pop(field,None)
 return {"algorithm":"sha256","value":hashlib.sha256(json.dumps(material,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()}
if capsule["capsule_kind"]=="bootstrap_publication":
 auth_name="records/bootstrap-authorizations/"+authorization_id+".json"
 if auth_name not in members: raise SystemExit("authorization member missing")
 auth_raw,auth_artifact=members[auth_name]; auth=strict_load(auth_raw)
 if auth.get("schema_version")!="semantic-guard-u10-bootstrap-provisioning-authorization/v1" or auth.get("authorization_id")!=authorization_id or auth.get("authorization_version")!="1.0.0" or auth.get("authorized_operation")!="publish_exact_initial_u10_root" or auth.get("human_decision")!="accept" or auth.get("decision_owner")!="human" or auth.get("target_root")!="/Library/Application Support/semantic-guard/u10" or auth.get("formal_authority")!="human_bootstrap_publication_decision_only" or auth.get("positive_assurance_allowed") is not False or seal(auth,"authorization_digest")!=auth.get("authorization_digest"): raise SystemExit("authorization chain invalid")
 plan_ref=auth.get("plan_ref",{}); plan_name=plan_ref.get("record_member")
 if plan_name!="records/bootstrap-plans/"+str(plan_ref.get("plan_id"))+".json" or plan_name not in members: raise SystemExit("plan member binding invalid")
 plan_raw,plan_artifact=members[plan_name]; plan=strict_load(plan_raw)
 if plan_artifact!=plan_ref.get("artifact_digest") or plan.get("plan_id")!=plan_ref.get("plan_id") or plan.get("plan_version")!=plan_ref.get("plan_version") or plan.get("schema_version")!="semantic-guard-u10-bootstrap-provisioning-plan/v1" or plan.get("target_root")!="/Library/Application Support/semantic-guard/u10" or plan.get("formal_authority")!="none" or plan.get("positive_assurance_allowed") is not False or seal(plan,"plan_digest")!=plan.get("plan_digest") or plan.get("plan_digest")!=plan_ref.get("semantic_digest"): raise SystemExit("plan chain invalid")
 kit=plan.get("bootstrap_kit_denominator",{}); operation="bootstrap-capsule"
else:
 request_name="records/bootstrap-runtime-observation-requests/"+authorization_id+".json"
 if request_name not in members: raise SystemExit("runtime observation request missing")
 request_raw,request_artifact=members[request_name]; request=strict_load(request_raw)
 if request.get("schema_version")!="semantic-guard-u10-bootstrap-runtime-observation-request/v1" or request.get("request_id")!=authorization_id or request.get("request_version")!="1.0.0" or request.get("authorized_operation")!="observe_exact_root_runtimes_only" or request.get("human_decision")!="accept" or request.get("decision_owner")!="human" or request.get("formal_authority")!="human_root_observation_decision_only" or request.get("positive_assurance_allowed") is not False or seal(request,"request_digest")!=request.get("request_digest"): raise SystemExit("runtime observation request chain invalid")
 kit=request.get("bootstrap_kit_denominator",{}); operation="observe-runtime-capsule"
entries=kit.get("entries",[])
if kit.get("status")!="closed" or kit.get("entry_count")!=len(entries) or seal({"entries":entries},"unused")!=kit.get("denominator_digest"): raise SystemExit("kit denominator invalid")
matches=[e for e in entries if e.get("role")=="initial_capsule_provisioner" and e.get("member")=="bootstrap/u10_initial_trust_provisioner.py"]
if len(matches)!=1 or matches[0].get("artifact_digest")!={"algorithm":"sha256","value":provisioner_expected}: raise SystemExit("provisioner plan binding invalid")
if "bootstrap/u10_initial_trust_provisioner.py" not in members: raise SystemExit("provisioner member missing")
code,code_digest=members["bootstrap/u10_initial_trust_provisioner.py"]
if code_digest!={"algorithm":"sha256","value":provisioner_expected}: raise SystemExit("provisioner digest mismatch")
g={"__name__":"__main__","__file__":"<u10-initial-capsule-provisioner>","_U10_INITIAL_CAPSULE_RAW":raw}
sys.argv=[g["__file__"],operation,authorization_id]
exec(compile(code,g["__file__"],"exec",dont_inherit=True),g,g)
'''


class CapsuleBuildError(RuntimeError):
    pass


def _strict_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise json.JSONDecodeError(f"duplicate object key: {key!r}", key, 0)
        value[key] = item
    return value


def _reject_nonfinite_json_constant(value: str) -> Any:
    raise json.JSONDecodeError(f"non-finite JSON number: {value}", value, 0)


def _strict_json_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise json.JSONDecodeError(f"non-finite JSON number: {value}", value, 0)
    return parsed


def strict_json_loads(raw: str | bytes | bytearray) -> Any:
    return json.loads(
        raw,
        object_pairs_hook=_strict_json_object,
        parse_constant=_reject_nonfinite_json_constant,
        parse_float=_strict_json_float,
    )


def _digest(raw: bytes) -> dict[str, str]:
    return {"algorithm": "sha256", "value": hashlib.sha256(raw).hexdigest()}


def _read_once(path: Path, *, root: Path) -> bytes:
    root = root.resolve(strict=True)
    path = Path(os.path.abspath(path))
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise CapsuleBuildError(f"member escaped root: {path}") from exc
    current = root
    for part in relative.parts[:-1]:
        current /= part
        observed = current.lstat()
        if stat.S_ISLNK(observed.st_mode) or not stat.S_ISDIR(
            observed.st_mode
        ):
            raise CapsuleBuildError(
                f"member parent is not one real directory: {current}"
            )
    before = path.lstat()
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise CapsuleBuildError(f"member is not one regular file: {path}")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(descriptor)
        identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
        if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns) != identity:
            raise CapsuleBuildError(f"member changed before read: {path}")
        chunks = []
        while True:
            block = os.read(descriptor, 1024 * 1024)
            if not block:
                break
            chunks.append(block)
        after = os.fstat(descriptor)
        if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) != identity:
            raise CapsuleBuildError(f"member changed during read: {path}")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _load_json(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = strict_json_loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CapsuleBuildError(f"invalid JSON: {label}") from exc
    if not isinstance(value, dict):
        raise CapsuleBuildError(f"JSON object required: {label}")
    return value


def build_capsule(*, authorization_path: Path, plan_path: Path, member_root: Path) -> tuple[bytes, str]:
    member_root = member_root.resolve(strict=True)
    authorization_raw = _read_once(authorization_path, root=member_root)
    plan_raw = _read_once(plan_path, root=member_root)
    authorization = _load_json(authorization_raw, "authorization")
    plan = _load_json(plan_raw, "plan")
    authorization_id = str(authorization.get("authorization_id", ""))
    plan_id = str(plan.get("plan_id", ""))
    names = {
        f"records/bootstrap-authorizations/{authorization_id}.json": Path(
            os.path.abspath(authorization_path)
        ),
        f"records/bootstrap-plans/{plan_id}.json": Path(
            os.path.abspath(plan_path)
        ),
    }
    for entry in plan.get("bootstrap_kit_denominator", {}).get("entries", []):
        names[str(entry["member"])] = member_root / str(entry["member"])
    generated = {
        "generated_broker_effective_path", "generated_broker_runtime_manifest",
        "generated_control_effective_path", "generated_control_runtime_manifest",
        "generated_bootstrap_provenance_binding", "generated_empty_lock_file",
    }
    for entry in plan.get("target_denominator", {}).get("entries", []):
        source = entry.get("source")
        if isinstance(source, str) and source not in generated:
            names[source] = member_root / source
    observation_ref = plan.get("root_observation_ref", {})
    for field in (
        "receipt_member",
        "broker_manifest_member",
        "control_manifest_member",
    ):
        member = observation_ref.get(field)
        if isinstance(member, str):
            names[member] = member_root / member
    members = []
    raw_members: dict[str, bytes] = {}
    for name, path in sorted(names.items()):
        raw = _read_once(path, root=member_root)
        raw_members[name] = raw
        members.append({"name": name, "encoding": "base64", "content": base64.b64encode(raw).decode("ascii"), "artifact_digest": _digest(raw)})
    capsule = {
        "schema_version": CAPSULE_SCHEMA,
        "capsule_kind": "bootstrap_publication",
        "invocation_id": authorization_id,
        "members": members,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    # Reuse the production validators without importing untrusted code into a
    # privileged process; this builder itself is an unprivileged candidate tool.
    provisioner_path = Path(__file__).with_name("u10_initial_trust_provisioner.py")
    specification = importlib.util.spec_from_file_location("_u10_capsule_validator", provisioner_path)
    if specification is None or specification.loader is None:
        raise CapsuleBuildError("provisioner validator unavailable")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    try:
        specification.loader.exec_module(module)
    finally:
        sys.modules.pop(specification.name, None)
    module.validate_bootstrap_plan(plan, raw_members)
    module.validate_bootstrap_authorization(authorization, plan=plan, plan_raw=plan_raw)
    if PROVISIONER_MEMBER not in raw_members:
        raise CapsuleBuildError(f"required member missing: {PROVISIONER_MEMBER}")
    raw = json.dumps(
        capsule,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8") + b"\n"
    capsule_digest = hashlib.sha256(raw).hexdigest()
    provisioner_digest = hashlib.sha256(raw_members[PROVISIONER_MEMBER]).hexdigest()
    directive = " ".join(
        [
            "/usr/bin/python3", "-I", "-S", "-B", "-c", shlex.quote(LOADER),
            shlex.quote(str(Path("CAPSULE_ABSOLUTE_PATH"))), capsule_digest,
            provisioner_digest, shlex.quote(authorization_id),
        ]
    )
    return raw, directive


def build_observation_capsule(
    *, observation_request_path: Path, member_root: Path
) -> tuple[bytes, str]:
    member_root = member_root.resolve(strict=True)
    request_raw = _read_once(observation_request_path, root=member_root)
    request = _load_json(request_raw, "runtime observation request")
    request_id = str(request.get("request_id", ""))
    names = {
        f"records/bootstrap-runtime-observation-requests/{request_id}.json": Path(
            os.path.abspath(observation_request_path)
        )
    }
    for entry in request.get("bootstrap_kit_denominator", {}).get("entries", []):
        names[str(entry["member"])] = member_root / str(entry["member"])
    members = []
    raw_members: dict[str, bytes] = {}
    for name, path in sorted(names.items()):
        raw = _read_once(path, root=member_root)
        raw_members[name] = raw
        members.append(
            {
                "name": name,
                "encoding": "base64",
                "content": base64.b64encode(raw).decode("ascii"),
                "artifact_digest": _digest(raw),
            }
        )
    provisioner_path = Path(__file__).with_name("u10_initial_trust_provisioner.py")
    specification = importlib.util.spec_from_file_location(
        "_u10_observation_capsule_validator", provisioner_path
    )
    if specification is None or specification.loader is None:
        raise CapsuleBuildError("provisioner validator unavailable")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    try:
        specification.loader.exec_module(module)
    finally:
        sys.modules.pop(specification.name, None)
    module.validate_runtime_observation_request(request, raw_members)
    if PROVISIONER_MEMBER not in raw_members:
        raise CapsuleBuildError(f"required member missing: {PROVISIONER_MEMBER}")
    capsule = {
        "schema_version": CAPSULE_SCHEMA,
        "capsule_kind": "root_runtime_observation",
        "invocation_id": request_id,
        "members": members,
        "formal_authority": "none",
        "positive_assurance_allowed": False,
    }
    raw = json.dumps(
        capsule,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8") + b"\n"
    capsule_digest = hashlib.sha256(raw).hexdigest()
    provisioner_digest = hashlib.sha256(raw_members[PROVISIONER_MEMBER]).hexdigest()
    directive = " ".join(
        [
            "/usr/bin/python3", "-I", "-S", "-B", "-c", shlex.quote(LOADER),
            shlex.quote(str(Path("CAPSULE_ABSOLUTE_PATH"))), capsule_digest,
            provisioner_digest, shlex.quote(request_id),
        ]
    )
    return raw, directive


def _write_new(path: Path, raw: bytes, mode: int) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), mode)
    try:
        offset = 0
        while offset < len(raw):
            offset += os.write(descriptor, raw[offset:])
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--authorization", type=Path)
    mode.add_argument("--observation-request", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--member-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--directive-output", required=True, type=Path)
    args = parser.parse_args()
    if args.observation_request is not None:
        if args.plan is not None:
            parser.error("--plan cannot be used with --observation-request")
        raw, directive = build_observation_capsule(
            observation_request_path=args.observation_request,
            member_root=args.member_root,
        )
    else:
        if args.plan is None:
            parser.error("--plan is required with --authorization")
        raw, directive = build_capsule(
            authorization_path=args.authorization,
            plan_path=args.plan,
            member_root=args.member_root,
        )
    directive = directive.replace("CAPSULE_ABSOLUTE_PATH", str(args.output.resolve(strict=False)))
    _write_new(args.output, raw, 0o400)
    _write_new(args.directive_output, (directive + "\n").encode("utf-8"), 0o400)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
