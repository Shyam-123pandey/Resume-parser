from candidate_transformer.extraction import extract_csv_row, extract_resume_text
from candidate_transformer.models import build_profile
from candidate_transformer.matching import deduplicate, match_reason


def _csv_profile():
    row = {"name": "John Doe", "email": "john@gmail.com", "phone": "9876543210"}
    record = extract_csv_row(row, source_id="c.csv", row_index=0)
    return build_profile(record)


def _resume_profile():
    text = "Jonathan Doe\njohn@gmail.com\n\nSkills:\nPython\n"
    record = extract_resume_text(text, source_id="r.txt")
    return build_profile(record)


def test_email_match_merges_profiles():
    p1, p2 = _csv_profile(), _resume_profile()
    assert match_reason(p1, p2) == "Matched on exact email address"

    merged = deduplicate([p1, p2])
    assert len(merged) == 1
    assert set(merged[0].sources) == {"c.csv#row0", "r.txt"}


def test_unrelated_profiles_are_not_merged():
    row_a = {"name": "Alice", "email": "alice@x.com"}
    row_b = {"name": "Bob", "email": "bob@y.com"}
    pa = build_profile(extract_csv_row(row_a, source_id="a.csv", row_index=0))
    pb = build_profile(extract_csv_row(row_b, source_id="b.csv", row_index=0))

    merged = deduplicate([pa, pb])
    assert len(merged) == 2
