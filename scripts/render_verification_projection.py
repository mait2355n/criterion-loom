from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from semantic_guard.verification_projection import (
    render_verification_projection,
)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Render or check the exact verification-source Markdown projection."
    )
    parser.add_argument(
        "--source",
        default=str(root / "validation/verification-source.json"),
    )
    parser.add_argument(
        "--output",
        default=str(root / "validation/verification-source.generated.md"),
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    source_path = Path(args.source).resolve()
    output_path = Path(args.output).resolve()
    source_bytes = source_path.read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    rendered = render_verification_projection(
        source,
        source_sha256=hashlib.sha256(source_bytes).hexdigest(),
        source_ref=source_path.name,
    )
    observed = output_path.read_text(encoding="utf-8") if output_path.exists() else None
    matches = observed == rendered
    if args.check:
        print(
            json.dumps(
                {
                    "status": "ok" if matches else "mismatch",
                    "source": str(source_path),
                    "output": str(output_path),
                    "matches": matches,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0 if matches else 1

    output_path.write_text(rendered, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "written",
                "source": str(source_path),
                "output": str(output_path),
                "sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
