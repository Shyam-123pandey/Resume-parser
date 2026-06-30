"""
Schema Validation Layer.

Validates the final projected output against a JSON Schema before it is
written out. The schema can be supplied in the run configuration; if not
supplied, a sensible default schema is generated based on the output
projection's field list and types found in the config.
"""

from __future__ import annotations

from typing import Any, Dict, List

import jsonschema


class ValidationError(Exception):
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_output(record: Dict[str, Any], schema: Dict[str, Any]) -> None:
    """Validates a single projected record against a JSON Schema.
    Raises ValidationError (collecting all problems) if invalid."""
    validator_cls = jsonschema.Draft7Validator
    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(record), key=lambda e: list(e.path))
    if errors:
        messages = [f"{'.'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors]
        raise ValidationError(messages)


def validate_all(records: List[Dict[str, Any]], schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Validates every record; returns the list of records that passed.
    Records that fail are dropped with an explanatory error attached for
    reporting, never silently included in valid output."""
    valid_records: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    for record in records:
        try:
            validate_output(record, schema)
            valid_records.append(record)
        except ValidationError as e:
            failures.append({"record": record, "errors": e.errors})
    if failures:
        raise PartialValidationFailure(valid_records, failures)
    return valid_records


class PartialValidationFailure(Exception):
    """Raised when some (not necessarily all) records fail validation.
    Carries both the records that passed and details on the ones that
    failed so the CLI can report a clear summary and still emit any valid
    output."""

    def __init__(self, valid_records: List[Dict[str, Any]], failures: List[Dict[str, Any]]):
        self.valid_records = valid_records
        self.failures = failures
        super().__init__(f"{len(failures)} record(s) failed schema validation")
