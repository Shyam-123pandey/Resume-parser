from __future__ import annotations

from pathlib import Path
from typing import List

from candidate_transformer.adapters.base import SourceAdapter
from candidate_transformer.extraction import extract_resume_text
from candidate_transformer.models import RawExtractedRecord


class ResumeAdapter(SourceAdapter):
    """Handles unstructured resume documents: .pdf, .docx, and .txt (plain
    text is supported as a convenient fallback / for testing without needing
    binary fixtures)."""

    handled_extensions = {".pdf", ".docx", ".txt"}

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in self.handled_extensions

    def extract(self, path: Path) -> List[RawExtractedRecord]:
        text = self._read_text(path)
        return [extract_resume_text(text, source_id=path.name)]

    def _read_text(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix == ".txt":
            return path.read_text(encoding="utf-8", errors="ignore")
        if suffix == ".pdf":
            return self._read_pdf(path)
        if suffix == ".docx":
            return self._read_docx(path)
        raise ValueError(f"Unsupported resume format: {suffix}")

    @staticmethod
    def _read_pdf(path: Path) -> str:
        try:
            from pypdf import PdfReader
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "pypdf is required to parse PDF resumes. Install with `pip install pypdf`."
            ) from e
        reader = PdfReader(str(path))
        pages_text = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages_text)

    @staticmethod
    def _read_docx(path: Path) -> str:
        try:
            import docx  # python-docx
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "python-docx is required to parse DOCX resumes. Install with `pip install python-docx`."
            ) from e
        document = docx.Document(str(path))
        return "\n".join(p.text for p in document.paragraphs)
