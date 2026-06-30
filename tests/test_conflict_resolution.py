from candidate_transformer.models import ExtractionMethod, FieldValue, Provenance, SourceType
from candidate_transformer.resolver import resolve_field


def _fv(value, source: SourceType, confidence: float):
    return FieldValue(
        value=value,
        confidence=confidence,
        provenance=Provenance(source=source, source_id="x", method=ExtractionMethod.EXACT_FIELD),
    )


def test_resolve_field_prefers_higher_priority_source():
    candidates = [
        _fv("Engineer", SourceType.CSV, 0.95),
        _fv("Senior Engineer", SourceType.ATS, 0.95),
    ]
    resolved = resolve_field("title", candidates, source_priority=["csv", "ats"])
    assert resolved.value == "Senior Engineer"
    assert resolved.source == SourceType.ATS


def test_resolve_field_single_candidate_short_circuits():
    candidates = [_fv("Acme", SourceType.CSV, 0.95)]
    resolved = resolve_field("company", candidates)
    assert resolved.value == "Acme"
    assert resolved.reason == "Only one candidate value available"


def test_resolve_field_keeps_full_candidate_history():
    candidates = [
        _fv("Engineer", SourceType.CSV, 0.95),
        _fv("Senior Engineer", SourceType.ATS, 0.95),
    ]
    resolved = resolve_field("title", candidates, source_priority=["csv", "ats"])
    assert len(resolved.candidates) == 2
