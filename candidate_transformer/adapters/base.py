"""
Source Adapter Layer.

Each adapter is responsible for reading a specific input format (CSV, PDF
resume, DOCX resume, and in the future ATS JSON, GitHub API, LinkedIn, etc.)
and producing one or more `RawExtractedRecord` instances via the Extraction
Layer. Adapters know about *file formats*; they delegate field-level
extraction logic to extractor functions in `candidate_transformer.extraction`
so that new sources can be added without touching the extraction logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from candidate_transformer.models import RawExtractedRecord


class SourceAdapter(ABC):
    """Base class for all source adapters."""

    #: file extensions this adapter claims to handle, e.g. {".csv"}
    handled_extensions: set[str] = set()

    @abstractmethod
    def can_handle(self, path: Path) -> bool:
        ...

    @abstractmethod
    def extract(self, path: Path) -> List[RawExtractedRecord]:
        """Read `path` and return a list of RawExtractedRecord (one per
        candidate record contained in the file)."""
        ...


class AdapterRegistry:
    """Holds all registered adapters and routes input files to the right
    one. New adapters (ATS JSON, GitHub, LinkedIn, ...) register themselves
    here without any other code needing to change.
    """

    def __init__(self) -> None:
        self._adapters: List[SourceAdapter] = []

    def register(self, adapter: SourceAdapter) -> None:
        self._adapters.append(adapter)

    def adapter_for(self, path: Path) -> SourceAdapter | None:
        for adapter in self._adapters:
            if adapter.can_handle(path):
                return adapter
        return None

    def extract_all(self, input_dir: Path) -> List[RawExtractedRecord]:
        records: List[RawExtractedRecord] = []
        for path in sorted(input_dir.rglob("*")):
            if not path.is_file():
                continue
            adapter = self.adapter_for(path)
            if adapter is None:
                continue  # unsupported file types are silently skipped
            records.extend(adapter.extract(path))
        return records


def default_registry() -> AdapterRegistry:
    """Builds the registry with all built-in adapters registered."""
    from candidate_transformer.adapters.csv_adapter import CsvAdapter
    from candidate_transformer.adapters.resume_adapter import ResumeAdapter

    registry = AdapterRegistry()
    registry.register(CsvAdapter())
    registry.register(ResumeAdapter())
    return registry
