"""
Email receipt importer (RM-117).
Skeleton implementation — extend with Python's email / mailparser when available.
"""

from pathlib import Path
from typing import Any, Dict, List

from .base_importer import BaseImporter


class EmailImporter(BaseImporter):
    """Handles email receipt files (.eml, .msg)."""

    @property
    def supported_extensions(self) -> List[str]:
        return [".eml", ".msg"]

    def can_import(self, path: Path) -> bool:
        return path.suffix.lower() in self.supported_extensions

    def extract(self, path: Path) -> Dict[str, Any]:
        """
        Extract data from an email receipt.
        Returns an empty skeleton; real extraction requires email / mailparser.
        """
        return {"shop": "", "purchase_date": "", "total_amount": None, "items": []}
