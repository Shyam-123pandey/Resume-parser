"""
Canonical internal data model for the Candidate Data Transformer Pipeline.

Every value that flows through the pipeline after extraction is wrapped in a
`FieldValue`, which carries the value itself plus confidence and provenance
metadata. This lets every downstream stage (normalization, matching, conflict
resolution, confidence scoring, projection) reason about *where a value came
from* and *how much it should be trusted*, not just what the value is.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    CSV = "csv"
    RESUME = "resume"
    ATS = "ats"
    GITHUB = "github"
    LINKEDIN = "linkedin"
    API = "api"
    UNKNOWN = "unknown"


class ExtractionMethod(str, Enum):
    EXACT_FIELD = "exact_field"          # e.g. CSV column, ATS API field
    TEXT_PATTERN = "text_pattern"        # regex/heuristic extraction from text
    TEXT_INFERENCE = "text_inference"    # heuristic/NLP-style guess
    API_EXTRACTION = "api_extraction"    # structured API response


class Provenance(BaseModel):
    """Where a field's value came from and how it was extracted."""

    source: SourceType
    source_id: str = Field(..., description="Identifier of the originating file/record, e.g. filename")
    method: ExtractionMethod
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_snippet: Optional[str] = Field(
        default=None, description="Optional raw text/snippet the value was derived from"
    )


class FieldValue(BaseModel):
    """A single candidate value for a field, with confidence + provenance.

    Multiple FieldValue entries for the same logical field (e.g. multiple
    'title' candidates from different sources) are what feed the Conflict
    Resolution Engine.
    """

    value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: Provenance
    reason: Optional[str] = Field(
        default=None, description="Why this value was extracted/assigned this confidence"
    )


class ResolvedField(BaseModel):
    """Output of conflict resolution: the chosen value plus the full history
    of candidate values that were considered."""

    value: Any
    source: SourceType
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    candidates: List[FieldValue] = Field(default_factory=list)


class ExperienceEntry(BaseModel):
    company: Optional[str] = None
    title: Optional[str] = None
    start_date: Optional[str] = None  # normalized to YYYY-MM where possible
    end_date: Optional[str] = None
    description: Optional[str] = None


class EducationEntry(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class RawExtractedRecord(BaseModel):
    """Intermediate representation produced by the Extraction Layer for a
    single input record/document, before being merged into the canonical
    CandidateProfile. This is the contract between Source Adapters and the
    Canonical Model builder.
    """

    source: SourceType
    source_id: str
    fields: Dict[str, List[FieldValue]] = Field(default_factory=dict)
    experience: List[FieldValue] = Field(default_factory=list)  # value=ExperienceEntry-like dict
    education: List[FieldValue] = Field(default_factory=list)   # value=EducationEntry-like dict
    skills: List[FieldValue] = Field(default_factory=list)      # value=str


class CandidateProfile(BaseModel):
    """The canonical internal candidate model.

    All raw inputs, regardless of source, are merged into instances of this
    model. Multi-valued fields (emails, phones, skills, experience,
    education) keep every distinct value with provenance. Single-valued
    fields that can conflict across sources (name, title, company, etc.) are
    represented as a dict of field-name -> ResolvedField once conflict
    resolution has run; before that they are stored as raw FieldValue lists
    in `pending_fields`.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Multi-valued, deduplicated-by-value fields
    emails: List[FieldValue] = Field(default_factory=list)
    phones: List[FieldValue] = Field(default_factory=list)
    skills: List[FieldValue] = Field(default_factory=list)
    experience: List[FieldValue] = Field(default_factory=list)
    education: List[FieldValue] = Field(default_factory=list)

    # Single-valued fields with multiple candidates, pending resolution
    pending_fields: Dict[str, List[FieldValue]] = Field(default_factory=dict)

    # Single-valued fields after conflict resolution
    resolved_fields: Dict[str, ResolvedField] = Field(default_factory=dict)

    sources: List[str] = Field(default_factory=list, description="Source ids merged into this profile")

    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    def add_source(self, source_id: str) -> None:
        if source_id not in self.sources:
            self.sources.append(source_id)
