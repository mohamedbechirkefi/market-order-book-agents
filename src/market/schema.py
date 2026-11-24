# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Versioned JSON schemas and a small validator (a subset of JSON Schema 2020-12).

Supported keywords: type, enum, required, properties, additionalProperties, items,
minimum, pattern. The schema files in ``schemas/`` are the contract the M5 demo reads.
"""

from __future__ import annotations

import json
import math
import re
from importlib import resources

RUN_RESULT_VERSION = "1.0.0"
RUN_MANIFEST_VERSION = "1.0.0"


class SchemaError(ValueError):
    """A document does not conform to its schema."""


def load_schema(name: str, version: str) -> dict:
    text = resources.files("market").joinpath("schemas", f"{name}-{version}.json").read_text(encoding="utf-8")
    return json.loads(text)


_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def validate(doc: object, schema: dict, path: str = "$") -> None:
    """Raise SchemaError with a JSON path on the first violation."""
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if not any(_TYPES[x](doc) for x in types):
            raise SchemaError(f"{path}: expected {types}, got {type(doc).__name__} ({doc!r:.60})")
    if "enum" in schema and doc not in schema["enum"]:
        raise SchemaError(f"{path}: {doc!r} not in {schema['enum']}")
    if "minimum" in schema and isinstance(doc, (int, float)) and not isinstance(doc, bool) and doc < schema["minimum"]:
        raise SchemaError(f"{path}: {doc} < minimum {schema['minimum']}")
    if "pattern" in schema and isinstance(doc, str) and not re.search(schema["pattern"], doc):
        raise SchemaError(f"{path}: {doc!r} does not match {schema['pattern']}")
    if isinstance(doc, dict):
        for key in schema.get("required", []):
            if key not in doc:
                raise SchemaError(f"{path}: missing required key {key!r}")
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for key, val in doc.items():
            if key in props:
                validate(val, props[key], f"{path}.{key}")
            elif extra is False:
                raise SchemaError(f"{path}: unexpected key {key!r}")
            elif isinstance(extra, dict):
                validate(val, extra, f"{path}.{key}")
    if isinstance(doc, list) and "items" in schema:
        for i, val in enumerate(doc):
            validate(val, schema["items"], f"{path}[{i}]")


def validate_run_result(doc: dict) -> dict:
    validate(doc, load_schema("run_result", RUN_RESULT_VERSION))
    if doc["status"] == "ok" and not doc["invariants"]["passed"]:
        raise SchemaError("$.status: 'ok' run with failed invariants")
    return doc


def validate_run_manifest(doc: dict) -> dict:
    validate(doc, load_schema("run_manifest", RUN_MANIFEST_VERSION))
    return doc


def dump_json(doc: object) -> str:
    """Deterministic JSON text; NaN and infinity are refused."""
    return json.dumps(doc, indent=2, sort_keys=True, allow_nan=False) + "\n"
