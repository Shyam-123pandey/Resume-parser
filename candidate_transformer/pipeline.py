"""
Pipeline Orchestrator.

Wires together every layer of the architecture in the required order:

  Input Sources -> Source Adapter Layer -> Extraction Layer
  -> Canonical Internal Candidate Model -> Normalization Engine
  -> Entity Matching/Deduplication Engine -> Conflict Resolution Engine
  -> Confidence Scoring Engine -> Provenance Tracking Layer
  -> Canonical Profile Store -> Configurable Output Projection Engine
  -> Schema Validation -> Final JSON Output
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from candidate_transformer.adapters import default_registry
from candidate_transformer.config import PipelineConfig
from candidate_transformer.confidence import compute_overall_confidence
from candidate_transformer.matching import deduplicate
from candidate_transformer.models import CanonicalProfileStore, build_profiles
from candidate_transformer.resolver import dedupe_multi_value_fields, resolve_conflicts
from candidate_transformer.validation import default_schema_for_config
from candidate_transformer.projection import project_profile


class PipelineResult:
    def __init__(self) -> None:
        self.output_records: List[Dict[str, Any]] = []
        self.validation_failures: List[Dict[str, Any]] = []
        self.profile_count: int = 0
        self.raw_record_count: int = 0


def run_pipeline(input_dir: Path, config: PipelineConfig) -> PipelineResult:
    result = PipelineResult()

    # 1. Input Sources -> 2. Source Adapter Layer -> 3. Extraction Layer
    registry = default_registry()
    raw_records = registry.extract_all(input_dir)
    result.raw_record_count = len(raw_records)

    # 4. Canonical Internal Candidate Model + 5. Normalization Engine
    profiles = build_profiles(raw_records)

    # 6. Entity Matching / Deduplication Engine
    merged_profiles = deduplicate(profiles)

    # 7. Conflict Resolution Engine (+ dedupe multi-value fields)
    for profile in merged_profiles:
        dedupe_multi_value_fields(profile)
        resolve_conflicts(profile, source_priority=config.source_priority)
        # 8. Confidence Scoring Engine
        profile.overall_confidence = compute_overall_confidence(profile)

    result.profile_count = len(merged_profiles)

    # 9. Provenance Tracking Layer happens inline as part of projection
    #    (see project_profile, which attaches the provenance trail).

    # 10. Canonical Profile Store
    store = CanonicalProfileStore()
    store.add_many(merged_profiles)

    # 11. Configurable Output Projection Engine
    output_config = config.output
    projected = [project_profile(p, output_config) for p in store.all()]

    # 12. Schema Validation
    schema = config.schema_ or default_schema_for_config(output_config)
    from candidate_transformer.validation import validate_output, ValidationError

    for record in projected:
        try:
            validate_output(record, schema)
            result.output_records.append(record)
        except ValidationError as e:
            result.validation_failures.append({"record": record, "errors": e.errors})

    return result
