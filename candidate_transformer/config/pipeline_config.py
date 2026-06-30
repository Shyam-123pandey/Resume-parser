"""
Runtime Configuration.

Loads `config.json`, which controls:
  - `source_priority`: ordered list of source names from lowest to highest
    authority, used by the Conflict Resolution Engine.
  - `output`: the Output Projection Engine configuration (field mapping).
  - `schema`: optional explicit JSON Schema for output validation; if
    omitted, one is derived from `output`.

This keeps output format and resolution behavior fully data-driven, with no
code changes required to support a new output shape.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


DEFAULT_OUTPUT_CONFIG: Dict[str, Any] = {
    "fields": [
        {"path": "id", "from": "id"},
        {"path": "name", "from": "resolved_fields.name.value"},
        {"path": "emails", "from": "emails"},
        {"path": "phone", "from": "phones[0].value", "normalize": "E164"},
        {"path": "title", "from": "resolved_fields.title.value"},
        {"path": "company", "from": "resolved_fields.company.value"},
        {"path": "skills", "from": "skills"},
        {"path": "experience", "from": "experience"},
        {"path": "education", "from": "education"},
        {"path": "sources", "from": "sources"},
    ],
    "include_confidence": True,
    "include_provenance": True,
    "include_sources": False,
}


class PipelineConfig(BaseModel):
    source_priority: Optional[List[str]] = None
    output: Dict[str, Any] = Field(default_factory=lambda: dict(DEFAULT_OUTPUT_CONFIG))
    schema_: Optional[Dict[str, Any]] = Field(default=None, alias="schema")
    default_country_code: str = "91"

    model_config = {"populate_by_name": True}

    @classmethod
    def load(cls, path: Path | None) -> "PipelineConfig":
        if path is None or not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(**data)
