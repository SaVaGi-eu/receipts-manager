"""
PDF receipt importer (RM-117).
Skeleton implementation — extend with pdfplumber / pymupdf when available.
"""

from pathlib import Path
from typing import Any, Dict, List

from .base_importer import BaseImporter


class PdfImporter(BaseImporter):
    """Handles PDF receipt files."""

    @property
    def supported_extensions(self) -> List[str]:
        return [".pdf"]

    def can_import(self, path: Path) -> bool:
        return path.suffix.lower() in self.supported_extensions

    def extract(self, path: Path) -> Dict[str, Any]:
        """
        Extract data from a PDF receipt.
        Returns an empty skeleton; real extraction requires pdfplumber or pymupdf.
        """
        return {"shop": "", "purchase_date": "", "total_amount": None, "items": []}
