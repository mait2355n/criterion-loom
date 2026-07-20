from __future__ import annotations

import json
from pathlib import Path
import sys


def main() -> None:
    payload = json.load(sys.stdin)
    root = Path(str(payload["legacy_root"])).resolve()
    sys.path.insert(0, str(root / "src"))

    from semantic_guard.audit_common import apply_logical_trace_mode
    from semantic_guard.request_audit import audit_request
    from semantic_guard.severity_profiles import apply_severity_profile

    result = audit_request(
        text=str(payload.get("text", "")),
        context=str(payload.get("context", "")),
        strict=bool(payload.get("strict", True)),
        input_kind="requirement",
    )
    result = apply_severity_profile(result, str(payload.get("profile", "default")))
    result = apply_logical_trace_mode(result, str(payload.get("logical_trace", "summary")))
    json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
