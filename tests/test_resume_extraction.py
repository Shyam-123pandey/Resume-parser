from candidate_transformer.extraction import extract_resume_text

SAMPLE_RESUME = """Jane Q. Public
jane@example.com
+1 415 555 1234

Skills:
Python3, AWS, Kubernetes

Experience:
Senior Engineer at Acme Corp (Jan 2020 - Present)

Education:
B.Sc Computer Science, MIT
"""


def test_resume_extracts_name_email_phone():
    record = extract_resume_text(SAMPLE_RESUME, source_id="jane.txt")
    names = [fv.value for fv in record.fields.get("name", [])]
    emails = [fv.value for fv in record.fields.get("emails", [])]
    assert "Jane Q. Public" in names
    assert "jane@example.com" in emails
    assert record.fields.get("phones")


def test_resume_extracts_skills():
    record = extract_resume_text(SAMPLE_RESUME, source_id="jane.txt")
    skills = [fv.value for fv in record.skills]
    assert "Python3" in skills
    assert "AWS" in skills


def test_resume_extracts_experience():
    record = extract_resume_text(SAMPLE_RESUME, source_id="jane.txt")
    assert len(record.experience) == 1
    entry = record.experience[0].value
    assert entry["title"] == "Senior Engineer"
    assert entry["company"] == "Acme Corp"
