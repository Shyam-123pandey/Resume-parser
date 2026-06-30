"""
Converts ExtractionLayer output (`RawExtractedRecord`) into the Canonical
Internal Candidate Model (`CandidateProfile`), applying the Normalization
Engine to every value along the way. One CandidateProfile is built per
input record; the Entity Matching/Deduplication Engine is responsible for
merging profiles that represent the same real person.
"""

from __future__ import annotations

import copy
from typing import List

from candidate_transformer.models.canonical import CandidateProfile, FieldValue, RawExtractedRecord
from candidate_transformer.normalization import (
    normalize_date,
    normalize_email,
    normalize_name,
    normalize_phone,
    normalize_skill,
)

SINGLE_VALUE_FIELDS = {"name", "title", "company"}


def _normalize_field_value(field_name: str, fv: FieldValue) -> FieldValue:
    new_fv = copy.deepcopy(fv)
    if field_name == "emails":
        new_fv.value = normalize_email(fv.value)
    elif field_name == "phones":
        new_fv.value = normalize_phone(fv.value)
    elif field_name == "name":
        new_fv.value = normalize_name(fv.value)
    elif field_name == "skills":
        new_fv.value = normalize_skill(fv.value)
    return new_fv


def _normalize_experience_entry(fv: FieldValue) -> FieldValue:
    new_fv = copy.deepcopy(fv)
    entry = dict(fv.value) if isinstance(fv.value, dict) else {}
    if entry.get("start_date"):
        entry["start_date"] = normalize_date(entry["start_date"])
    if entry.get("end_date"):
        entry["end_date"] = normalize_date(entry["end_date"])
    new_fv.value = entry
    return new_fv


def _normalize_education_entry(fv: FieldValue) -> FieldValue:
    new_fv = copy.deepcopy(fv)
    entry = dict(fv.value) if isinstance(fv.value, dict) else {}
    if entry.get("start_date"):
        entry["start_date"] = normalize_date(entry["start_date"])
    if entry.get("end_date"):
        entry["end_date"] = normalize_date(entry["end_date"])
    new_fv.value = entry
    return new_fv


def build_profile(record: RawExtractedRecord) -> CandidateProfile:
    profile = CandidateProfile()
    profile.add_source(record.source_id)

    for field_name, values in record.fields.items():
        for fv in values:
            normalized = _normalize_field_value(field_name, fv)
            if normalized.value is None:
                continue
            if field_name == "emails":
                profile.emails.append(normalized)
            elif field_name == "phones":
                profile.phones.append(normalized)
            elif field_name in SINGLE_VALUE_FIELDS:
                profile.pending_fields.setdefault(field_name, []).append(normalized)
            else:
                profile.pending_fields.setdefault(field_name, []).append(normalized)

    for fv in record.skills:
        normalized = _normalize_field_value("skills", fv)
        if normalized.value:
            profile.skills.append(normalized)

    for fv in record.experience:
        profile.experience.append(_normalize_experience_entry(fv))

    for fv in record.education:
        profile.education.append(_normalize_education_entry(fv))

    return profile


def build_profiles(records: List[RawExtractedRecord]) -> List[CandidateProfile]:
    return [build_profile(r) for r in records]
