"""
Extraction logic for unstructured resume text (sourced from PDF or DOCX).

This module works purely on plain text already pulled out of the document
(the adapter handles PDF/DOCX parsing). It uses regex/heuristic extraction,
which is appropriate for an MVP and keeps the dependency footprint small
while still being clearly extensible (swap in an NLP model later without
changing the adapter or downstream pipeline).
"""

from __future__ import annotations

import re
from typing import List

from candidate_transformer.confidence import default_confidence
from candidate_transformer.models import (
    EducationEntry,
    ExperienceEntry,
    ExtractionMethod,
    FieldValue,
    Provenance,
    RawExtractedRecord,
    SourceType,
)

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")

SECTION_HEADERS = {
    "skills": re.compile(r"^\s*(skills|technical skills|core competencies)\s*:?\s*$", re.IGNORECASE),
    "experience": re.compile(r"^\s*(experience|work experience|employment history)\s*:?\s*$", re.IGNORECASE),
    "education": re.compile(r"^\s*(education|academic background)\s*:?\s*$", re.IGNORECASE),
}

KNOWN_SECTION_NAMES = {"skills", "experience", "education", "summary", "objective",
                        "projects", "certifications", "contact", "profile"}


def _split_sections(lines: List[str]) -> dict:
    sections: dict = {}
    current = "header"
    sections[current] = []
    for line in lines:
        matched_section = None
        for name, pattern in SECTION_HEADERS.items():
            if pattern.match(line):
                matched_section = name
                break
        if matched_section:
            current = matched_section
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


def _extract_name(lines: List[str]) -> str | None:
    # Heuristic: the first non-empty line that isn't an email/phone and
    # doesn't look like a section header is treated as the candidate name.
    for line in lines[:5]:
        text = line.strip()
        if not text:
            continue
        if EMAIL_RE.search(text) or PHONE_RE.search(text):
            continue
        if text.lower() in KNOWN_SECTION_NAMES:
            continue
        # Names are typically short lines (<= 5 words)
        if len(text.split()) <= 5:
            return text
    return None


def _extract_skills(skill_lines: List[str]) -> List[str]:
    text = " ".join(skill_lines)
    if not text.strip():
        return []
    # Split on commas, semicolons, pipes, or bullet characters.
    parts = re.split(r"[,;|•\u2022\n]+", text)
    skills = [p.strip() for p in parts if p.strip()]
    return skills


def _extract_experience(exp_lines: List[str]) -> List[dict]:
    """Very light heuristic parser: looks for lines like
    'Title at Company (Jan 2020 - Present)' or 'Title, Company - 2019 - 2021'.
    Falls back to storing the raw line as a description if it doesn't match.
    """
    entries: List[dict] = []
    date_range_re = re.compile(
        r"(?P<start>[A-Za-z]+\.?\s+\d{4}|\d{4}[/-]\d{1,2}|\d{4})\s*[-–to]+\s*(?P<end>[A-Za-z]+\.?\s+\d{4}|\d{4}[/-]\d{1,2}|\d{4}|Present|present|Current|current)"
    )
    for raw_line in exp_lines:
        line = raw_line.strip()
        if not line:
            continue
        entry: dict = {}
        date_match = date_range_re.search(line)
        if date_match:
            entry["start_date"] = date_match.group("start")
            entry["end_date"] = date_match.group("end")
            line_wo_dates = line[: date_match.start()].strip(" -,()")
        else:
            line_wo_dates = line

        # "Title at Company" or "Title, Company" or "Title - Company"
        m = re.match(r"^(?P<title>[^,@\-]+?)\s+(?:at|@)\s+(?P<company>.+)$", line_wo_dates)
        if not m:
            m = re.match(r"^(?P<title>[^,]+),\s*(?P<company>.+)$", line_wo_dates)
        if m:
            entry["title"] = m.group("title").strip()
            entry["company"] = m.group("company").strip()
        elif line_wo_dates:
            entry["description"] = line_wo_dates

        if entry:
            entries.append(entry)
    return entries


def _extract_education(edu_lines: List[str]) -> List[dict]:
    entries: List[dict] = []
    for raw_line in edu_lines:
        line = raw_line.strip()
        if not line:
            continue
        entry: dict = {}
        m = re.match(r"^(?P<degree>[^,]+),\s*(?P<institution>.+)$", line)
        if m:
            entry["degree"] = m.group("degree").strip()
            entry["institution"] = m.group("institution").strip()
        else:
            entry["institution"] = line
        entries.append(entry)
    return entries


def extract_resume_text(text: str, source_id: str, source_type: SourceType = SourceType.RESUME) -> RawExtractedRecord:
    record = RawExtractedRecord(source=source_type, source_id=source_id)
    lines = [l for l in text.splitlines()]

    sections = _split_sections(lines)
    header_lines = sections.get("header", [])
    full_text = "\n".join(lines)

    # --- Name (text inference: low confidence heuristic) -----------------
    name = _extract_name(header_lines or lines)
    if name:
        conf = default_confidence(source_type, ExtractionMethod.TEXT_INFERENCE)
        record.fields.setdefault("name", []).append(
            FieldValue(
                value=name,
                confidence=conf,
                provenance=Provenance(
                    source=source_type,
                    source_id=source_id,
                    method=ExtractionMethod.TEXT_INFERENCE,
                    raw_snippet=name,
                ),
                reason="First non-contact line of resume header inferred as candidate name",
            )
        )

    # --- Emails / phones (text pattern: higher confidence regex match) ---
    for email in set(EMAIL_RE.findall(full_text)):
        conf = default_confidence(source_type, ExtractionMethod.TEXT_PATTERN)
        record.fields.setdefault("emails", []).append(
            FieldValue(
                value=email,
                confidence=conf,
                provenance=Provenance(
                    source=source_type, source_id=source_id,
                    method=ExtractionMethod.TEXT_PATTERN, raw_snippet=email,
                ),
                reason="Regex email pattern match in resume text",
            )
        )

    for phone in set(PHONE_RE.findall(full_text)):
        digits = re.sub(r"\D", "", phone)
        if len(digits) < 10:
            continue
        conf = default_confidence(source_type, ExtractionMethod.TEXT_PATTERN)
        record.fields.setdefault("phones", []).append(
            FieldValue(
                value=phone.strip(),
                confidence=conf,
                provenance=Provenance(
                    source=source_type, source_id=source_id,
                    method=ExtractionMethod.TEXT_PATTERN, raw_snippet=phone,
                ),
                reason="Regex phone pattern match in resume text",
            )
        )

    # --- Skills (text pattern) --------------------------------------------
    for skill in _extract_skills(sections.get("skills", [])):
        conf = default_confidence(source_type, ExtractionMethod.TEXT_PATTERN)
        record.skills.append(
            FieldValue(
                value=skill,
                confidence=conf,
                provenance=Provenance(
                    source=source_type, source_id=source_id,
                    method=ExtractionMethod.TEXT_PATTERN, raw_snippet=skill,
                ),
                reason="Parsed from resume 'Skills' section",
            )
        )

    # --- Experience (text inference: structure isn't guaranteed) ---------
    for entry in _extract_experience(sections.get("experience", [])):
        conf = default_confidence(source_type, ExtractionMethod.TEXT_INFERENCE)
        record.experience.append(
            FieldValue(
                value=entry,
                confidence=conf,
                provenance=Provenance(
                    source=source_type, source_id=source_id,
                    method=ExtractionMethod.TEXT_INFERENCE,
                    raw_snippet=str(entry),
                ),
                reason="Heuristically parsed from resume 'Experience' section",
            )
        )

    # --- Education (text inference) ---------------------------------------
    for entry in _extract_education(sections.get("education", [])):
        conf = default_confidence(source_type, ExtractionMethod.TEXT_INFERENCE)
        record.education.append(
            FieldValue(
                value=entry,
                confidence=conf,
                provenance=Provenance(
                    source=source_type, source_id=source_id,
                    method=ExtractionMethod.TEXT_INFERENCE,
                    raw_snippet=str(entry),
                ),
                reason="Heuristically parsed from resume 'Education' section",
            )
        )

    return record
