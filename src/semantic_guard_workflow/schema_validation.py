from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from jsonschema import Draft202012Validator, ValidationError, validators


def _nonblank_min_length(validator: Any, minimum: int, instance: object, schema: dict) -> Any:
    yield from Draft202012Validator.VALIDATORS["minLength"](validator, minimum, instance, schema)
    # Preserve the review validators' existing whitespace-only rejection. This
    # is an additional local constraint; JSON Schema minLength counts whitespace.
    if isinstance(instance, str) and minimum > 0 and len(instance) >= minimum and not instance.strip():
        yield ValidationError("must be a non-empty string")


_ReviewSchemaValidator = validators.extend(Draft202012Validator, {"minLength": _nonblank_min_length})


def _review_schema_errors(
    payload: object,
    schema: Mapping[str, Any],
    *,
    diagnostic_overrides: Mapping[tuple[tuple[str | int, ...], str], str] | None = None,
) -> list[str]:
    """Use the published schema while retaining established review diagnostics."""
    errors: list[str] = []
    overrides = diagnostic_overrides or {}
    for error in _ReviewSchemaValidator(schema).iter_errors(payload):
        path = "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in error.absolute_path).lstrip(".")
        override = overrides.get((tuple(error.absolute_path), error.validator))
        if override:
            errors.append(override)
        elif error.validator == "required":
            prefix = f"{path} " if path else ""
            errors.extend(
                f"{prefix}missing required field: {key}"
                for key in sorted(error.validator_value)
                if key not in error.instance
            )
        elif error.validator == "additionalProperties":
            errors.extend(
                f"{path} has unexpected field: {key}" if path else f"unexpected field: {key}"
                for key in sorted(set(error.instance) - set(error.schema.get("properties", {})))
            )
        elif error.validator == "enum":
            errors.append(f"{path} must be one of {sorted(error.validator_value)}")
        elif error.validator == "minLength":
            errors.append(f"{path} must be a non-empty string")
        elif error.validator == "type":
            kind = error.validator_value
            article = "an" if kind in {"object", "array", "integer"} else "a"
            errors.append(f"{path or 'payload'} must be {article} {kind}")
        else:
            errors.append(f"{error.json_path}: {error.message}")
    return list(dict.fromkeys(errors))
