from candidate_transformer.projection import project


def test_project_resolves_dotted_and_index_paths():
    profile_dict = {
        "id": "123",
        "resolved_fields": {"name": {"value": "John Doe"}},
        "phones": [{"value": "+919876543210"}],
        "overall_confidence": 0.9,
    }
    config = {
        "fields": [
            {"path": "id", "from": "id"},
            {"path": "name", "from": "resolved_fields.name.value"},
            {"path": "phone", "from": "phones[0].value"},
        ],
        "include_confidence": True,
    }

    output = project(profile_dict, config)
    assert output["id"] == "123"
    assert output["name"] == "John Doe"
    assert output["phone"] == "+919876543210"
    assert output["overall_confidence"] == 0.9


def test_project_applies_e164_normalize():
    profile_dict = {"phones": [{"value": "9876543210"}]}
    config = {"fields": [{"path": "phone", "from": "phones[0].value", "normalize": "E164"}]}
    output = project(profile_dict, config)
    assert output["phone"] == "+919876543210"


def test_project_missing_path_returns_none():
    profile_dict = {}
    config = {"fields": [{"path": "name", "from": "resolved_fields.name.value"}]}
    output = project(profile_dict, config)
    assert output["name"] is None
