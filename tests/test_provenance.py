from candidate_transformer.extraction import extract_csv_row
from candidate_transformer.models import build_profile
from candidate_transformer.provenance import build_provenance_trail


def test_provenance_trail_includes_source_and_method():
    row = {"name": "John Doe", "email": "john@gmail.com"}
    record = extract_csv_row(row, source_id="c.csv", row_index=0)
    profile = build_profile(record)

    trail = build_provenance_trail(profile)
    email_entries = [e for e in trail if e["field"] == "emails"]
    assert len(email_entries) == 1
    assert email_entries[0]["source"] == "csv"
    assert email_entries[0]["method"] == "exact_field"
    assert email_entries[0]["value"] == "john@gmail.com"
