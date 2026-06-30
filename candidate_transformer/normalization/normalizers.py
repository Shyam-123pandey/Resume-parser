"""
Normalization Engine.

Pure functions that take a raw extracted value and return a normalized,
canonical representation. These are deliberately dependency-light (no
external phone/date libraries) so the MVP stays simple to install, while
still handling the cases called out in the spec.
"""

from __future__ import annotations

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Phone normalization -> E.164-ish format, defaulting to India (+91) when no
# country code is present and the local number is 10 digits, since that is
# the example given in the spec. This default is configurable.
# ---------------------------------------------------------------------------

DEFAULT_COUNTRY_CODE = "91"


def normalize_phone(raw: str, default_country_code: str = DEFAULT_COUNTRY_CODE) -> Optional[str]:
    if not raw:
        return None

    digits = re.sub(r"[^\d+]", "", raw)
    has_plus = digits.startswith("+")
    digits = digits.lstrip("+")

    if not digits:
        return None

    if has_plus:
        return f"+{digits}"

    # No explicit country code given.
    if len(digits) == 10:
        return f"+{default_country_code}{digits}"

    # Already includes a country code without the '+', e.g. 919876543210
    if len(digits) > 10:
        return f"+{digits}"

    # Anything shorter than 10 digits is not a usable phone number.
    return None


# ---------------------------------------------------------------------------
# Date normalization -> YYYY-MM (month precision is what resumes/CSVs
# typically provide; falls back to YYYY-MM-DD if a full date is given).
# ---------------------------------------------------------------------------

_MONTHS = {
    "jan": "01", "january": "01",
    "feb": "02", "february": "02",
    "mar": "03", "march": "03",
    "apr": "04", "april": "04",
    "may": "05",
    "jun": "06", "june": "06",
    "jul": "07", "july": "07",
    "aug": "08", "august": "08",
    "sep": "09", "sept": "09", "september": "09",
    "oct": "10", "october": "10",
    "nov": "11", "november": "11",
    "dec": "12", "december": "12",
}

_PRESENT_WORDS = {"present", "current", "now", "ongoing", "today"}


def normalize_date(raw: str) -> Optional[str]:
    if not raw:
        return None
    text = raw.strip()
    if not text:
        return None

    if text.lower() in _PRESENT_WORDS:
        return "present"

    # YYYY-MM-DD
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", text)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{mo.zfill(2)}-{d.zfill(2)}"

    # YYYY/MM or YYYY-MM
    m = re.match(r"^(\d{4})[/-](\d{1,2})$", text)
    if m:
        y, mo = m.groups()
        return f"{y}-{mo.zfill(2)}"

    # "Jan 2020", "January 2020"
    m = re.match(r"^([A-Za-z]+)\.?\s+(\d{4})$", text)
    if m:
        month_word, year = m.groups()
        month_num = _MONTHS.get(month_word.lower())
        if month_num:
            return f"{year}-{month_num}"

    # "2020 Jan"
    m = re.match(r"^(\d{4})\s+([A-Za-z]+)\.?$", text)
    if m:
        year, month_word = m.groups()
        month_num = _MONTHS.get(month_word.lower())
        if month_num:
            return f"{year}-{month_num}"

    # MM/YYYY
    m = re.match(r"^(\d{1,2})/(\d{4})$", text)
    if m:
        mo, y = m.groups()
        return f"{y}-{mo.zfill(2)}"

    # Just a year
    m = re.match(r"^(\d{4})$", text)
    if m:
        return f"{m.group(1)}"

    # Unable to confidently normalize; return original trimmed text.
    return text


# ---------------------------------------------------------------------------
# Skill normalization -> canonical skill names via an alias map + light
# heuristics (strip version numbers/suffixes like "programming", "developer").
# ---------------------------------------------------------------------------

_SKILL_ALIASES = {
    "py": "Python",
    "python3": "Python",
    "python 3": "Python",
    "python programming": "Python",
    "python development": "Python",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "reactjs": "React",
    "react.js": "React",
    "react": "React",
    "aws": "AWS",
    "amazon web services": "AWS",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "tf": "TensorFlow",
    "tensorflow": "TensorFlow",
    "golang": "Go",
    "go lang": "Go",
}

_SKILL_NOISE_SUFFIXES = [
    " programming", " development", " developer", " language", " framework",
]


def normalize_skill(raw: str) -> Optional[str]:
    if not raw:
        return None
    text = raw.strip()
    if not text:
        return None

    key = text.lower()
    key = re.sub(r"\s+", " ", key)

    if key in _SKILL_ALIASES:
        return _SKILL_ALIASES[key]

    # Strip trailing version numbers, e.g. "python3" handled above;
    # generic "Foo 2" -> "Foo"
    stripped = re.sub(r"\s*\d+(\.\d+)*$", "", key).strip()
    if stripped in _SKILL_ALIASES:
        return _SKILL_ALIASES[stripped]

    for suffix in _SKILL_NOISE_SUFFIXES:
        if key.endswith(suffix):
            base = key[: -len(suffix)].strip()
            if base in _SKILL_ALIASES:
                return _SKILL_ALIASES[base]
            return base.title()

    # Fallback: title-case the cleaned string for consistent display.
    return stripped.title() if stripped else text.title()


# ---------------------------------------------------------------------------
# Name normalization -> collapse whitespace, title-case, used for display +
# as an input to fuzzy matching (matching has its own similarity logic).
# ---------------------------------------------------------------------------

def normalize_name(raw: str) -> Optional[str]:
    if not raw:
        return None
    text = re.sub(r"\s+", " ", raw.strip())
    if not text:
        return None
    # Preserve all-caps acronyms within names rarely matter for people names;
    # simple title-case is sufficient for an MVP.
    return text.title()


def normalize_email(raw: str) -> Optional[str]:
    if not raw:
        return None
    return raw.strip().lower()
