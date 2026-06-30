"""
Configurable Output Projection Engine.

Reads a runtime JSON configuration describing the desired output shape and
projects a `CandidateProfile` into that shape, without any code changes
required for new output formats. Supports dotted/bracket paths into the
canonical profile (e.g. "phones[0]", "resolved_fields.title.value") and
optional per-field normalization hints.

Example config field entry:
    {"path": "name", "from": "resolved_fields.name.value"}
    {"path": "phone", "from": "phones[0].value", "normalize": "E164"}
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from candidate_transformer.normalization import normalize_phone
from candidate_transformer.provenance import build_provenance_trail

_INDEX_RE = re.compile(r"^(\w+)\[(\d+)\]$")


def _resolve_path(data: Any, path: str) -> Any:
    """Resolves a dotted path like 'resolved_fields.title.value' or
    'phones[0].value' against a (possibly nested) dict/list structure."""
    current = data
    for part in path.split("."):
        if current is None:
            return None
        m = _INDEX_RE.match(part)
        if m:
            key, idx = m.group(1), int(m.group(2))
            if isinstance(current, dict):
                current = current.get(key)
            else:
                current = None
            if isinstance(current, list):
                current = current[idx] if 0 <= idx < len(current) else None
            else:
                current = None
        else:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                # allow plain numeric segments too
                try:
                    current = current[int(part)]
                except (ValueError, IndexError):
                    current = None
            else:
                current = None
    return current


def _apply_normalize(value: Any, normalize: str | None) -> Any:
    if value is None or not normalize:
        return value
    if normalize.upper() == "E164":
        return normalize_phone(value) if isinstance(value, str) else value
    if normalize.upper() == "LOWER":
        return value.lower() if isinstance(value, str) else value
    if normalize.upper() == "UPPER":
        return value.upper() if isinstance(value, str) else value
    return value


def _set_output_path(output: dict, path: str, value: Any) -> None:
    """Sets a (possibly nested, dot-separated) path in the output dict,
    creating intermediate dicts as needed. Output paths do not support list
    indices -- only the source path does."""
    parts = path.split(".")
    current = output
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value


def project(profile_dict: Dict[str, Any], output_config: Dict[str, Any]) -> Dict[str, Any]:
    """Projects a profile (already dict-ified via model_dump) into the
    shape described by `output_config`.

    output_config schema:
        {
          "fields": [{"path": "<output key>", "from": "<source path>", "normalize": "<optional>"}],
          "include_confidence": true,
          "include_provenance": false
        }
    """
    output: Dict[str, Any] = {}

    for field_spec in output_config.get("fields", []):
        out_path = field_spec["path"]
        source_path = field_spec["from"]
        value = _resolve_path(profile_dict, source_path)
        value = _apply_normalize(value, field_spec.get("normalize"))
        _set_output_path(output, out_path, value)

    if output_config.get("include_confidence", False):
        output["overall_confidence"] = profile_dict.get("overall_confidence")

    if output_config.get("include_provenance", False):
        output["provenance"] = profile_dict.get("_provenance_trail", [])

    if output_config.get("include_sources", False):
        output["sources"] = profile_dict.get("sources", [])

    return output


def project_profile(profile, output_config: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience wrapper: takes a CandidateProfile model instance, dumps
    it, attaches a provenance trail, and projects it."""
    profile_dict = profile.model_dump(mode="json")
    profile_dict["_provenance_trail"] = build_provenance_trail(profile)
    return project(profile_dict, output_config)


def project_all(profiles: List, output_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [project_profile(p, output_config) for p in profiles]
