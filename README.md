# Multi-Source Candidate Data Transformer Pipeline

> A CLI tool that ingests candidate data from multiple heterogeneous sources
> (structured CSVs, unstructured resumes, and more), converts every input into
> a single clean, validated, deduplicated **canonical candidate profile**, and
> emits configurable JSON output — without ever transforming a source directly
> into the output format.

##  Design Philosophy & Technical Decisions

This project was built to showcase the ability to design a **clean data pipeline**, handle **messy real-world inputs**, and make **thoughtful software engineering decisions**. 

Key design decisions include:
- **Separation of Concerns:** Raw sources are never transformed directly into the output schema. Everything passes through an intermediate canonical model.
- **Intelligent Conflict Resolution:** When sources disagree (e.g., a CSV vs. a Resume on a job title), the pipeline uses configurable priority rules rather than arbitrary overwrites.
- **Auditability (Provenance):** Every single data point maintains a strict audit trail (provenance) and a confidence score, ensuring that data hygiene can always be verified in a production environment.
- **Extensibility:** Adding a new data source (like a new ATS API) requires zero changes to the core normalization, deduplication, or validation logic.

---

## Architecture

```
Input Sources
   -> Source Adapter Layer        (candidate_transformer/adapters)
   -> Extraction Layer            (candidate_transformer/extraction)
   -> Canonical Internal Model    (candidate_transformer/models)
   -> Normalization Engine        (candidate_transformer/normalization)
   -> Entity Matching/Dedup       (candidate_transformer/matching)
   -> Conflict Resolution Engine  (candidate_transformer/resolver)
   -> Confidence Scoring Engine   (candidate_transformer/confidence)
   -> Provenance Tracking Layer   (candidate_transformer/provenance)
   -> Canonical Profile Store     (candidate_transformer/models/store.py)
   -> Output Projection Engine    (candidate_transformer/projection)
   -> Schema Validation           (candidate_transformer/validation)
   -> Final JSON Output
```

Every input file is **always** routed through a source adapter, an
extractor, and the normalization engine before it ever touches a
`CandidateProfile`. Nothing transforms a raw source straight into output.

### How Each Layer Works

| Layer | Directory | What It Does |
|-------|-----------|--------------|
| **Adapters** | `adapters/` | Know about file formats (`.csv`, `.pdf`, `.docx`, `.txt`). Adding a new source (ATS JSON, GitHub API, LinkedIn export) means writing one adapter + extractor pair and registering it in `adapters/base.py::default_registry`. |
| **Extraction** | `extraction/` | Converts raw input into an intermediate `RawExtractedRecord`: a bag of `FieldValue`s, each carrying a confidence score and provenance from the moment it is created. |
| **Canonical Model** | `models/canonical.py` | Defines `CandidateProfile` — `id`, `emails`, `phones`, `skills`, `experience`, `education`, `pending_fields`/`resolved_fields`, `sources`, and `overall_confidence`. |
| **Normalization** | `normalization/` | Standardizes phones (`98765 43210` → `+919876543210`), dates (`Jan 2020` → `2020-01`), skills (`Py` → `Python`), names, and emails. |
| **Matching/Dedup** | `matching/` | Merges profiles of the same person: **email match → phone match → name similarity → experience/employer overlap**. |
| **Conflict Resolution** | `resolver/` | Picks the best value for single-valued fields using a configurable `source_priority` list, keeping every candidate value for auditability. |
| **Confidence Scoring** | `confidence/` | Assigns default confidence by source/method (CSV exact = 0.95, resume pattern = 0.80, resume inference = 0.50) and computes a weighted overall score. |
| **Provenance Tracking** | `provenance/` | Compiles a flat audit trail of every field's source, extraction method, and timestamp. |
| **Profile Store** | `models/store.py` | In-memory + optional JSON dump — swap in a real DB later without touching the rest of the pipeline. |
| **Projection** | `projection/` | Maps the canonical profile into whatever shape the caller wants, driven entirely by `config.json`. |
| **Validation** | `validation/` | Checks projected output against a JSON Schema; invalid records are reported and excluded, never silently passed through. |

---

## Installation

**Requires Python 3.10+.**

```bash
# 1. Install in editable mode
pip install -e .
```

This installs the `candidate-transformer` console command along with its
dependencies (`pydantic`, `jsonschema`, `pypdf`, `python-docx`).

### Running Tests

```bash
pip install -r requirements.txt
pytest
```

---

## CLI Usage

**Option 1** — Using the installed console script (available after `pip install -e .`):

```bash
candidate-transformer --input <INPUT_DIR> --config <CONFIG_FILE> --output <OUTPUT_FILE>
```

**Option 2** — Using the Python module directly (no install needed):

```bash
python -m candidate_transformer.cli.main --input data/ --config config.json --output candidate.json
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--input` | Yes | — | Directory containing input files. The tool **recursively** scans this directory and all subdirectories for supported formats: `.csv`, `.pdf`, `.docx`, `.txt`. Unsupported file types are silently skipped. |
| `--config` | No | Built-in defaults | Path to a `config.json` controlling source priority and output shape. |
| `--output` | No | `candidate.json` | Where the final JSON output is written. |

---

## Quick Start with Sample Data

The project ships with sample data in `data/sample_input/`:

| File | Type | Contents |
|------|------|----------|
| `candidates.csv` | Structured CSV | 2 candidates with `name, email, phone, company, title` columns |
| `jonathan_doe_resume.txt` | Unstructured resume | Resume for "Jonathan Doe" (same person as "John Doe" in the CSV — shares email `john@gmail.com`) |

### Run the Pipeline

```bash
# Both of these work — the tool recursively scans for supported files
candidate-transformer --input data/sample_input --config config.json --output candidate.json
candidate-transformer --input data/ --config config.json --output candidate.json
```

### Expected Output

```
Ingested 3 raw record(s) from 'data/sample_input'
Resolved into 2 canonical candidate profile(s)
Wrote 2 valid record(s) to 'candidate.json'
```

---

## Configuration Format (`config.json`)

```json
{
  "source_priority": ["resume", "csv", "linkedin", "github", "ats"],
  "output": {
    "fields": [
      {"path": "id", "from": "id"},
      {"path": "name", "from": "resolved_fields.name.value"},
      {"path": "emails", "from": "emails"},
      {"path": "phone", "from": "phones[0].value", "normalize": "E164"},
      {"path": "title", "from": "resolved_fields.title.value"},
      {"path": "company", "from": "resolved_fields.company.value"},
      {"path": "skills", "from": "skills"},
      {"path": "experience", "from": "experience"},
      {"path": "education", "from": "education"},
      {"path": "sources", "from": "sources"}
    ],
    "include_confidence": true,
    "include_provenance": true
  },
  "schema": null
}
```

### Configuration Keys

| Key | Description |
|-----|-------------|
| `source_priority` | Ordered list (lowest → highest authority) used by the Conflict Resolution Engine when sources disagree on a single-valued field (`name`, `title`, `company`). |
| `output.fields` | Each entry maps an **output key** (`path`, dot-notation for nesting) to a **source path** (`from`, supports dotted access and `field[index]` syntax). Optional `normalize` hint: `E164`, `LOWER`, `UPPER`. |
| `output.include_confidence` | Adds `overall_confidence` to each output record. |
| `output.include_provenance` | Adds a flat `provenance` audit trail to each output record. |
| `schema` | Optional explicit JSON Schema to validate output against. If omitted, a schema is derived automatically from `output.fields`. |

---

## Extending the Pipeline

To add a new source (e.g. ATS JSON, GitHub, LinkedIn):

1. **Add an extractor** in `extraction/` that converts the source's native
   format into a `RawExtractedRecord` of `FieldValue`s (set
   `source=SourceType.ATS` / `GITHUB` / `LINKEDIN` and an appropriate
   `ExtractionMethod`).

2. **Add an adapter** in `adapters/` implementing `SourceAdapter` that reads
   the file and calls your extractor.

3. **Register the adapter** in `adapters/base.py::default_registry`.

That's it! No changes are needed to normalization, matching, conflict
resolution, confidence scoring, provenance, projection, or validation — they
all operate on the canonical model, not the source format.

---

## Project Structure

```
candidate-transformer/
├── candidate_transformer/
│   ├── adapters/          # Source Adapter Layer (CSV, Resume)
│   ├── cli/               # CLI entry point
│   ├── confidence/        # Confidence Scoring Engine
│   ├── config/            # Pipeline configuration loader
│   ├── extraction/        # Extraction Layer (CSV rows, resume text)
│   ├── matching/          # Entity Matching / Deduplication
│   ├── models/            # Canonical Model + Profile Store + Builder
│   ├── normalization/     # Normalization Engine (phone, date, skill, etc.)
│   ├── projection/        # Output Projection Engine
│   ├── provenance/        # Provenance Tracking Layer
│   ├── resolver/          # Conflict Resolution Engine
│   ├── validation/        # Schema Validation Layer
│   └── pipeline.py        # Pipeline Orchestrator
├── data/
│   └── sample_input/      # Sample CSV + resume for testing
├── tests/                 # Test suite
├── config.json            # Default pipeline configuration
├── pyproject.toml         # Package metadata
└── requirements.txt       # Dev/test dependencies
```

---

## Future Enhancements

- **Web Interface:** Build a lightweight FastAPI backend and a modern frontend (e.g., React/Vite) to visually demonstrate the deduplication and conflict resolution via a drag-and-drop UI.
- **Database Integration:** Swap the in-memory profile store for a persistent database (PostgreSQL/MongoDB) without altering the pipeline logic.
