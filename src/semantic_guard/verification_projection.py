"""Deterministic readable projection for the canonical verification source.

The projection is deliberately generated from the complete parsed source.  A
compact inventory helps human navigation, while the JSON-Pointer appendix
preserves every scalar value and every container boundary without pretending
that prose paraphrase is a proof of semantic equivalence.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping


PROJECTION_VERSION = "semantic-guard-verification-projection/v0"
_DIRECT_COLLECTIONS = (
    "state_profiles",
    "evidence_observations",
    "evidence_effects",
    "verification_items",
    "implementation_conformance_items",
    "views",
    "unresolved_items",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_json_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _node_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


def iter_pointer_records(value: Any, pointer: str = "") -> Iterable[dict[str, Any]]:
    """Yield deterministic records for every JSON node."""

    node_type = _node_type(value)
    record: dict[str, Any] = {
        "pointer": pointer or "/",
        "node_type": node_type,
    }
    if isinstance(value, dict):
        record["member_count"] = len(value)
        record["keys"] = sorted(value)
    elif isinstance(value, list):
        record["item_count"] = len(value)
    else:
        record["value"] = value
    yield record

    if isinstance(value, dict):
        for key in sorted(value):
            child_pointer = f"{pointer}/{_pointer_token(key)}"
            yield from iter_pointer_records(value[key], child_pointer)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from iter_pointer_records(item, f"{pointer}/{index}")


def _entity_id(item: Mapping[str, Any]) -> str | None:
    for field in ("entity_id", "effect_id", "obligation_id", "path_id"):
        value = item.get(field)
        if isinstance(value, str):
            return value
    return None


def _short_label(item: Mapping[str, Any]) -> str:
    for field in ("label", "title", "subject", "proposition", "responsibility"):
        value = item.get(field)
        if isinstance(value, str) and value:
            return value if len(value) <= 120 else f"{value[:117]}..."
    return ""


def _inventory(source: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for collection in _DIRECT_COLLECTIONS:
        values = source.get(collection, [])
        if not isinstance(values, list):
            continue
        for item in values:
            if not isinstance(item, dict):
                continue
            identifier = _entity_id(item)
            if identifier is not None:
                rows.append((collection, identifier, _short_label(item)))
            if collection == "unresolved_items":
                for nested_collection, id_field in (
                    ("resolution_obligations", "obligation_id"),
                    ("resolution_paths", "path_id"),
                ):
                    for nested in item.get(nested_collection, []):
                        if isinstance(nested, dict) and isinstance(
                            nested.get(id_field), str
                        ):
                            rows.append(
                                (
                                    nested_collection,
                                    nested[id_field],
                                    _short_label(nested),
                                )
                            )
    return sorted(rows)


def _markdown_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")


def render_verification_projection(
    source: Mapping[str, Any],
    *,
    source_sha256: str,
    source_ref: str = "verification-source.json",
) -> str:
    """Render the exact deterministic Markdown projection."""

    acceptance = source.get("human_acceptance", {})
    lines = [
        "# Verification Source Generated Projection",
        "",
        "> GENERATED FILE. Edit `verification-source.json`, then regenerate this file.",
        "> Exact equality is checked by `validate_verification_source.py`.",
        "",
        "## Binding",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| projection_version | `{PROJECTION_VERSION}` |",
        f"| source | `{_markdown_cell(source_ref)}` |",
        f"| source_sha256 | `{source_sha256}` |",
        f"| canonical_json_sha256 | `{canonical_json_sha256(source)}` |",
        f"| schema_version | `{_markdown_cell(source.get('schema_version'))}` |",
        f"| register_id | `{_markdown_cell(source.get('register_id'))}` |",
        f"| recorded_at | `{_markdown_cell(source.get('recorded_at'))}` |",
        f"| human_acceptance.status | `{_markdown_cell(acceptance.get('status'))}` |",
        f"| human_acceptance.owner | `{_markdown_cell(acceptance.get('owner'))}` |",
        "",
        "## Collection Counts",
        "",
        "| Collection | Count |",
        "| --- | ---: |",
    ]
    for collection in _DIRECT_COLLECTIONS:
        values = source.get(collection, [])
        count = len(values) if isinstance(values, list) else 0
        lines.append(f"| `{collection}` | {count} |")
    unresolved = source.get("unresolved_items", [])
    if isinstance(unresolved, list):
        for nested_collection in ("resolution_obligations", "resolution_paths"):
            count = sum(
                len(item.get(nested_collection, []))
                for item in unresolved
                if isinstance(item, dict)
                and isinstance(item.get(nested_collection, []), list)
            )
            lines.append(f"| `{nested_collection}` | {count} |")

    lines.extend(
        [
            "",
            "## Entity Inventory",
            "",
            "| Collection | Stable ID | Navigation label |",
            "| --- | --- | --- |",
        ]
    )
    for collection, identifier, label in _inventory(source):
        lines.append(
            f"| `{collection}` | `{_markdown_cell(identifier)}` | "
            f"{_markdown_cell(label)} |"
        )

    pointer_records = list(iter_pointer_records(source))
    lines.extend(
        [
            "",
            "## Complete JSON-Pointer Value Appendix",
            "",
            "Every source node appears exactly once below. Object records expose their",
            "sorted keys, array records expose their length, and scalar records expose the",
            "complete JSON value. JSON Pointer escaping follows RFC 6901.",
            "",
            f"Node count: `{len(pointer_records)}`",
            "",
            "```jsonl",
        ]
    )
    lines.extend(_canonical_json(record) for record in pointer_records)
    lines.extend(["```", ""])
    return "\n".join(lines)
