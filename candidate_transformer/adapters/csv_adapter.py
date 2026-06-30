from __future__ import annotations

import csv
from pathlib import Path
from typing import List

from candidate_transformer.adapters.base import SourceAdapter
from candidate_transformer.extraction import extract_csv_row
from candidate_transformer.models import RawExtractedRecord


class CsvAdapter(SourceAdapter):
    handled_extensions = {".csv"}

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in self.handled_extensions

    def extract(self, path: Path) -> List[RawExtractedRecord]:
        records: List[RawExtractedRecord] = []
        with path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                records.append(extract_csv_row(row, source_id=path.name, row_index=i))
        return records
