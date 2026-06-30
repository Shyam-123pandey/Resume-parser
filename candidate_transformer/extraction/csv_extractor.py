"""
Extraction logic for structured CSV input.

Converts a raw CSV row into the intermediate `RawExtractedRecord`
representation. Field-name aliases are supported so loosely-formatted CSVs
(different header casing/naming) still extract cleanly.
"""

from __future__ import annotations

from typing import Dict, List

from candidate_transformer.confidence import default_confidence
from candidate_transformer.models import (
    ExtractionMethod,
    FieldValue,
    Provenance,
    RawExtractedRecord,
    SourceType,
)

# header aliasing: canonical_field -> set of accepted header names (lowercased)
CSV_FIELD_ALIASES: Dict[str, set] = {
    "name": {"name", "full_name", "fullname", "candidate_name"},
    "email": {"email", "email_address", "e-mail"},
    "phone": {"phone", "phone_number", "mobile", "contact_number"},
    "company": {"company", "current_company", "employer"},
    "title": {"title", "job_title", "designation", "role"},
}


def _match_header(header: str) -> str | None:
    h = header.strip().lower()
    for canonical, aliases in CSV_FIELD_ALIASES.items():
        if h in aliases:
            return canonical
    return None


def extract_csv_row(row: Dict[str, str], source_id: str, row_index: int) -> RawExtractedRecord:
    record = RawExtractedRecord(source=SourceType.CSV, source_id=f"{source_id}#row{row_index}")

    for header, raw_value in row.items():
        if header is None or raw_value is None:
            continue
        canonical = _match_header(header)
        if canonical is None:
            continue
        value = str(raw_value).strip()
        if not value:
            continue

        confidence = default_confidence(SourceType.CSV, ExtractionMethod.EXACT_FIELD)
        provenance = Provenance(
            source=SourceType.CSV,
            source_id=record.source_id,
            method=ExtractionMethod.EXACT_FIELD,
            raw_snippet=f"{header}={raw_value}",
        )
        field_value = FieldValue(
            value=value,
            confidence=confidence,
            provenance=provenance,
            reason=f"CSV column '{header}' mapped directly to '{canonical}'",
        )

        if canonical == "email":
            record.fields.setdefault("emails", []).append(field_value)
        elif canonical == "phone":
            record.fields.setdefault("phones", []).append(field_value)
        else:
            record.fields.setdefault(canonical, []).append(field_value)

    return record
