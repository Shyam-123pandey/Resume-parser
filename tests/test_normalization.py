from candidate_transformer.normalization import (
    normalize_date,
    normalize_phone,
    normalize_skill,
)


def test_normalize_phone_local_number():
    assert normalize_phone("98765 43210") == "+919876543210"


def test_normalize_phone_with_country_code():
    assert normalize_phone("+91-9876543210") == "+919876543210"


def test_normalize_phone_too_short_returns_none():
    assert normalize_phone("12345") is None


def test_normalize_date_month_year():
    assert normalize_date("Jan 2020") == "2020-01"


def test_normalize_date_slash_format():
    assert normalize_date("2020/01") == "2020-01"


def test_normalize_date_present():
    assert normalize_date("Present") == "present"


def test_normalize_skill_aliases():
    assert normalize_skill("Py") == "Python"
    assert normalize_skill("Python3") == "Python"
    assert normalize_skill("Python programming") == "Python"
