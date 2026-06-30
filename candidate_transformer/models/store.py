"""
Canonical Profile Store.

A minimal store for finalized CandidateProfile objects. For this MVP the
store is in-memory plus an optional JSON dump to disk -- enough to act as
the persistence boundary the architecture calls for, while staying simple.
It is intentionally behind a small interface so a real database-backed
store could be swapped in later without touching the rest of the pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from candidate_transformer.models.canonical import CandidateProfile


class CanonicalProfileStore:
    def __init__(self) -> None:
        self._profiles: List[CandidateProfile] = []

    def add(self, profile: CandidateProfile) -> None:
        self._profiles.append(profile)

    def add_many(self, profiles: List[CandidateProfile]) -> None:
        self._profiles.extend(profiles)

    def all(self) -> List[CandidateProfile]:
        return list(self._profiles)

    def get(self, candidate_id: str) -> CandidateProfile | None:
        for p in self._profiles:
            if p.id == candidate_id:
                return p
        return None

    def dump_to_file(self, path: Path) -> None:
        path.write_text(
            json.dumps([p.model_dump(mode="json") for p in self._profiles], indent=2, default=str),
            encoding="utf-8",
        )
