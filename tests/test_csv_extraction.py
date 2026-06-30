from candidate_transformer.extraction import extract_csv_row


def test_csv_extraction_maps_known_fields():
    row = {"name": "John", "email": "a@gmail.com", "phone": "9876543210",
           "company": "Acme", "title": "Engineer"}
    record = extract_csv_row(row, source_id="test.csv", row_index=0)

    assert record.fields["name"][0].value == "John"
    assert record.fields["emails"][0].value == "a@gmail.com"
    assert record.fields["phones"][0].value == "9876543210"
    assert record.fields["company"][0].value == "Acme"
    assert record.fields["title"][0].value == "Engineer"
    assert record.fields["name"][0].confidence == 0.95


def test_csv_extraction_ignores_unknown_columns():
    row = {"name": "John", "favorite_color": "blue"}
    record = extract_csv_row(row, source_id="test.csv", row_index=0)
    assert "favorite_color" not in record.fields
