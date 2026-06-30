"""
Provenance Tracking Layer.

Provenance is captured at the point of extraction (every `FieldValue`
carries a `Provenance` object) and preserved through normalization,
matching, and conflict resolution. This module compiles that scattered
information into a single flat audit trail for a resolved profile, useful
for debugging, compliance, and optional inclusion in output.
"""

from __future__ import annotations

from typing import Any, Dict, List

from candidate_transformer.models import CandidateProfile


def _entry(field: str, fv) -> Dict[str, Any]:
    return {
        "field": field,
        "value": fv.value,
        "source": fv.provenance.source.value,
        "source_id": fv.provenance.source_id,
        "method": fv.provenance.method.value,
        "confidence": fv.confidence,
        "extracted_at": fv.provenance.extracted_at.isoformat(),
        "reason": fv.reason,
    }


def build_provenance_trail(profile: CandidateProfile) -> List[Dict[str, Any]]:
    trail: List[Dict[str, Any]] = []

    for fv in profile.emails:
        trail.append(_entry("emails", fv))
    for fv in profile.phones:
        trail.append(_entry("phones", fv))
    for fv in profile.skills:
        trail.append(_entry("skills", fv))
    for fv in profile.experience:
        trail.append(_entry("experience", fv))
    for fv in profile.education:
        trail.append(_entry("education", fv))

    for field_name, resolved in profile.resolved_fields.items():
        for fv in resolved.candidates:
            trail.append(_entry(field_name, fv))

    trail.sort(key=lambda e: (e["field"], e["source"]))
    return trail
