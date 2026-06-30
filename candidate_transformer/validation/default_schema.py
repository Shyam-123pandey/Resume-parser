"""
Builds a default JSON Schema for the projected output when the run
configuration does not supply an explicit one. Required fields and basic
types are inferred from the projection config's field list and simple type
hints (e.g. "type": "string") that may be attached to each field spec.
"""

from __future__ import annotations

from typing import Any, Dict


def default_schema_for_config(output_config: Dict[str, Any]) -> Dict[str, Any]:
    properties: Dict[str, Any] = {}
    required = []

    for field_spec in output_config.get("fields", []):
        path_parts = field_spec["path"].split(".")
        top_key = path_parts[0]
        field_type = field_spec.get("type", "string")
        properties.setdefault(top_key, {"type": ["string", "object", "array", "null"]})
        if field_spec.get("required", False):
            required.append(top_key)
        if "type" in field_spec:
            properties[top_key] = {"type": [field_type, "null"]} if field_spec.get("nullable", True) else {"type": field_type}

    if output_config.get("include_confidence", False):
        properties["overall_confidence"] = {"type": "number", "minimum": 0, "maximum": 1}

    schema: Dict[str, Any] = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": properties,
    }
    if required:
        schema["required"] = required
    return schema
