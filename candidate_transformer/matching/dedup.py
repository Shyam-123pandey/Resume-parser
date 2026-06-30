"""
Entity Matching / Deduplication Engine.

Determines whether two CandidateProfile instances represent the same real
person, using a priority order: email exact match > phone match > name
similarity > experience similarity. Matching profiles are merged together
(all field candidates from both are kept, with full provenance) before
being handed to the Conflict Resolution Engine.
"""

from __future__ import annotations

import difflib
from typing import List

from candidate_transformer.models import CandidateProfile

NAME_SIMILARITY_THRESHOLD = 0.82
EXPERIENCE_SIMILARITY_THRESHOLD = 0.6


def _emails(profile: CandidateProfile) -> set:
    return {fv.value for fv in profile.emails if fv.value}


def _phones(profile: CandidateProfile) -> set:
    return {fv.value for fv in profile.phones if fv.value}


def _names(profile: CandidateProfile) -> List[str]:
    return [fv.value for fv in profile.pending_fields.get("name", []) if fv.value]


def _companies(profile: CandidateProfile) -> set:
    return {
        (entry.value.get("company") or "").strip().lower()
        for entry in profile.experience
        if isinstance(entry.value, dict) and entry.value.get("company")
    }


def _name_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def emails_match(p1: CandidateProfile, p2: CandidateProfile) -> bool:
    return bool(_emails(p1) & _emails(p2))


def phones_match(p1: CandidateProfile, p2: CandidateProfile) -> bool:
    return bool(_phones(p1) & _phones(p2))


def names_similar(p1: CandidateProfile, p2: CandidateProfile) -> bool:
    names1, names2 = _names(p1), _names(p2)
    for n1 in names1:
        for n2 in names2:
            if _name_similarity(n1, n2) >= NAME_SIMILARITY_THRESHOLD:
                return True
    return False


def experience_similar(p1: CandidateProfile, p2: CandidateProfile) -> bool:
    companies1, companies2 = _companies(p1), _companies(p2)
    if not companies1 or not companies2:
        return False
    overlap = companies1 & companies2
    smaller = min(len(companies1), len(companies2))
    return smaller > 0 and (len(overlap) / smaller) >= EXPERIENCE_SIMILARITY_THRESHOLD


def match_reason(p1: CandidateProfile, p2: CandidateProfile) -> str | None:
    """Returns a human-readable reason if profiles match, else None.
    Checks matching signals in priority order as required by the spec."""
    if emails_match(p1, p2):
        return "Matched on exact email address"
    if phones_match(p1, p2):
        return "Matched on exact phone number"
    if names_similar(p1, p2):
        return "Matched on name similarity"
    if experience_similar(p1, p2):
        return "Matched on overlapping employer/experience"
    return None


def _merge_into(target: CandidateProfile, other: CandidateProfile) -> None:
    target.emails.extend(other.emails)
    target.phones.extend(other.phones)
    target.skills.extend(other.skills)
    target.experience.extend(other.experience)
    target.education.extend(other.education)
    for field_name, values in other.pending_fields.items():
        target.pending_fields.setdefault(field_name, []).extend(values)
    for source_id in other.sources:
        target.add_source(source_id)


def deduplicate(profiles: List[CandidateProfile]) -> List[CandidateProfile]:
    """Greedy union-find-style merge: repeatedly merge any pair of profiles
    that match, until no more merges are possible."""
    merged: List[CandidateProfile] = list(profiles)
    changed = True
    while changed:
        changed = False
        for i in range(len(merged)):
            for j in range(i + 1, len(merged)):
                if match_reason(merged[i], merged[j]) is not None:
                    _merge_into(merged[i], merged[j])
                    del merged[j]
                    changed = True
                    break
            if changed:
                break
    return merged
