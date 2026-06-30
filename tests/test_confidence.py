from candidate_transformer.confidence import default_confidence, compute_overall_confidence
from candidate_transformer.models import CandidateProfile, ExtractionMethod, FieldValue, Provenance, SourceType


def test_default_confidence_rules():
    assert default_confidence(SourceType.ATS, ExtractionMethod.EXACT_FIELD) == 0.95
    assert default_confidence(SourceType.CSV, ExtractionMethod.EXACT_FIELD) == 0.95
    assert default_confidence(SourceType.RESUME, ExtractionMethod.TEXT_PATTERN) == 0.80
    assert default_confidence(SourceType.RESUME, ExtractionMethod.TEXT_INFERENCE) == 0.50


def test_overall_confidence_is_weighted_average():
    profile = CandidateProfile()
    profile.emails.append(FieldValue(
        value="a@x.com", confidence=0.95,
        provenance=Provenance(source=SourceType.CSV, source_id="x", method=ExtractionMethod.EXACT_FIELD),
    ))
    profile.skills.append(FieldValue(
        value="Python", confidence=0.50,
        provenance=Provenance(source=SourceType.RESUME, source_id="x", method=ExtractionMethod.TEXT_INFERENCE),
    ))

    overall = compute_overall_confidence(profile)
    assert 0.0 < overall < 1.0


def test_overall_confidence_zero_when_no_fields():
    profile = CandidateProfile()
    assert compute_overall_confidence(profile) == 0.0
