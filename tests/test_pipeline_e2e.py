from pathlib import Path

from candidate_transformer.config import PipelineConfig
from candidate_transformer.pipeline import run_pipeline


def test_end_to_end_pipeline_merges_csv_and_resume(tmp_path: Path):
    csv_content = "name,email,phone,company,title\nJohn Doe,john@gmail.com,9876543210,Acme,Engineer\n"
    (tmp_path / "candidates.csv").write_text(csv_content, encoding="utf-8")

    resume_content = (
        "Jonathan Doe\njohn@gmail.com\n\nSkills:\nPython, AWS\n\n"
        "Experience:\nSenior Engineer at Acme (Jan 2020 - Present)\n"
    )
    (tmp_path / "jonathan.txt").write_text(resume_content, encoding="utf-8")

    config = PipelineConfig()
    result = run_pipeline(tmp_path, config)

    assert result.raw_record_count == 2
    assert result.profile_count == 1  # merged via shared email
    assert len(result.output_records) == 1

    record = result.output_records[0]
    assert record["name"] == "John Doe"
    assert record["phone"] == "+919876543210"
    assert "overall_confidence" in record
    assert record["provenance"]
