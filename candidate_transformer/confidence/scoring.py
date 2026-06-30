"""
Confidence Scoring Engine.

Provides the default confidence rules requested in the spec, and computes
overall candidate confidence as a weighted average of field-level confidence
scores.
"""

from __future__ import annotations

from typing import Dict, List

from candidate_transformer.models import (
    CandidateProfile,
    ExtractionMethod,
    FieldValue,
    SourceType,
)

# Default confidence by (source, method). Falls back to method-based default
# if the exact (source, method) pair is not listed.
DEFAULT_CONFIDENCE_BY_SOURCE_METHOD: Dict[tuple, float] = {
    (SourceType.ATS, ExtractionMethod.EXACT_FIELD): 0.95,
    (SourceType.CSV, ExtractionMethod.EXACT_FIELD): 0.95,
    (SourceType.RESUME, ExtractionMethod.TEXT_PATTERN): 0.80,
    (SourceType.RESUME, ExtractionMethod.TEXT_INFERENCE): 0.50,
    (SourceType.GITHUB, ExtractionMethod.API_EXTRACTION): 0.90,
    (SourceType.LINKEDIN, ExtractionMethod.API_EXTRACTION): 0.90,
}

DEFAULT_CONFIDENCE_BY_METHOD: Dict[ExtractionMethod, float] = {
    ExtractionMethod.EXACT_FIELD: 0.95,
    ExtractionMethod.API_EXTRACTION: 0.90,
    ExtractionMethod.TEXT_PATTERN: 0.80,
    ExtractionMethod.TEXT_INFERENCE: 0.50,
}

# Relative importance of each field when computing overall confidence.
FIELD_WEIGHTS: Dict[str, float] = {
    "name": 3.0,
    "emails": 2.5,
    "phones": 1.5,
    "title": 1.5,
    "company": 1.0,
    "skills": 2.0,
    "experience": 2.0,
    "education": 1.0,
}
DEFAULT_FIELD_WEIGHT = 1.0


def default_confidence(source: SourceType, method: ExtractionMethod) -> float:
    if (source, method) in DEFAULT_CONFIDENCE_BY_SOURCE_METHOD:
        return DEFAULT_CONFIDENCE_BY_SOURCE_METHOD[(source, method)]
    return DEFAULT_CONFIDENCE_BY_METHOD.get(method, 0.50)


def _best_confidence(values: List[FieldValue]) -> float:
    if not values:
        return 0.0
    return max(v.confidence for v in values)


def compute_overall_confidence(profile: CandidateProfile) -> float:
    """Weighted average across all known fields on the profile, using the
    best (highest-confidence) candidate available for each field."""

    weighted_sum = 0.0
    weight_total = 0.0

    def add(field_name: str, confidence: float, present: bool):
        nonlocal weighted_sum, weight_total
        if not present:
            return
        w = FIELD_WEIGHTS.get(field_name, DEFAULT_FIELD_WEIGHT)
        weighted_sum += w * confidence
        weight_total += w

    add("emails", _best_confidence(profile.emails), bool(profile.emails))
    add("phones", _best_confidence(profile.phones), bool(profile.phones))
    add("skills", _best_confidence(profile.skills), bool(profile.skills))
    add("experience", _best_confidence(profile.experience), bool(profile.experience))
    add("education", _best_confidence(profile.education), bool(profile.education))

    for field_name, resolved in profile.resolved_fields.items():
        add(field_name, resolved.confidence, True)

    if weight_total == 0.0:
        return 0.0

    return round(weighted_sum / weight_total, 4)
