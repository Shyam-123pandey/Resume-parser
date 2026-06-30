from .conflict_resolution import (
    resolve_field,
    resolve_conflicts,
    dedupe_multi_value_fields,
    DEFAULT_SOURCE_PRIORITY,
)

__all__ = [
    "resolve_field",
    "resolve_conflicts",
    "dedupe_multi_value_fields",
    "DEFAULT_SOURCE_PRIORITY",
]
