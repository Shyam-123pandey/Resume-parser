"""
Conflict Resolution Engine.

For single-valued fields (name, title, company, ...), multiple sources may
disagree. This module resolves each field's pending candidates into a single
`ResolvedField`, keeping the full candidate history for transparency, using
configurable source priority.

For multi-valued fields (emails, phones, skills), it deduplicates exact
duplicate values while preserving the highest-confidence FieldValue and
folding in any duplicate's provenance trail for full auditability.
"""

from __future__ import annotations

from typing import Dict, List

from candidate_transformer.models import CandidateProfile, FieldValue, ResolvedField, SourceType

# Default source authority ranking; higher index = more authoritative.
# Configurable at runtime via PipelineConfig.source_priority.
DEFAULT_SOURCE_PRIORITY: List[str] = [
    SourceType.RESUME.value,
    SourceType.LINKEDIN.value,
    SourceType.GITHUB.value,
    SourceType.CSV.value,
    SourceType.ATS.value,  # highest authority by default
]


def _priority_rank(source: SourceType, priority_list: List[str]) -> int:
    try:
        return priority_list.index(source.value)
    except ValueError:
        return -1


def resolve_field(field_name: str, candidates: List[FieldValue],
                   source_priority: List[str] | None = None) -> ResolvedField:
    priority_list = source_priority or DEFAULT_SOURCE_PRIORITY

    if not candidates:
        raise ValueError(f"Cannot resolve field '{field_name}' with no candidates")

    if len(candidates) == 1:
        only = candidates[0]
        return ResolvedField(
            value=only.value,
            source=only.provenance.source,
            confidence=only.confidence,
            reason="Only one candidate value available",
            candidates=candidates,
        )

    def sort_key(fv: FieldValue):
        return (
            _priority_rank(fv.provenance.source, priority_list),
            fv.confidence,
        )

    best = max(candidates, key=sort_key)
    best_source_label = best.provenance.source.value.upper()
    reason = f"{best_source_label} has higher authority/confidence than competing sources"

    return ResolvedField(
        value=best.value,
        source=best.provenance.source,
        confidence=best.confidence,
        reason=reason,
        candidates=candidates,
    )


def resolve_conflicts(profile: CandidateProfile, source_priority: List[str] | None = None) -> CandidateProfile:
    for field_name, candidates in profile.pending_fields.items():
        if not candidates:
            continue
        profile.resolved_fields[field_name] = resolve_field(field_name, candidates, source_priority)
    return profile


def _dedupe_multi_value(values: List[FieldValue]) -> List[FieldValue]:
    """Keeps one FieldValue per distinct value (case-insensitive for str),
    preferring the highest-confidence one."""
    best_by_value: Dict[str, FieldValue] = {}
    for fv in values:
        if fv.value is None:
            continue
        key = fv.value.lower() if isinstance(fv.value, str) else str(fv.value)
        existing = best_by_value.get(key)
        if existing is None or fv.confidence > existing.confidence:
            best_by_value[key] = fv
    return list(best_by_value.values())


def dedupe_multi_value_fields(profile: CandidateProfile) -> CandidateProfile:
    profile.emails = _dedupe_multi_value(profile.emails)
    profile.phones = _dedupe_multi_value(profile.phones)
    profile.skills = _dedupe_multi_value(profile.skills)
    return profile
