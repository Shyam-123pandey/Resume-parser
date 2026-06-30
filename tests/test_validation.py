import pytest

from candidate_transformer.validation import validate_output, ValidationError


def test_validation_passes_for_valid_record():
    schema = {
        "type": "object",
        "properties": {"phone": {"type": ["string", "null"]}},
    }
    validate_output({"phone": "+919876543210"}, schema)  # should not raise


def test_validation_fails_when_phone_is_not_string():
    schema = {
        "type": "object",
        "properties": {"phone": {"type": "string"}},
        "required": ["phone"],
    }
    with pytest.raises(ValidationError):
        validate_output({"phone": 12345}, schema)


def test_validation_fails_for_missing_required_field():
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    }
    with pytest.raises(ValidationError):
        validate_output({}, schema)
