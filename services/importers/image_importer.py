"""
Image receipt importer (RM-117).
Skeleton implementation — extend with Tesseract / cloud OCR when available.
"""

from pathlib import Path
from typing import Any, Dict, List

from .base_importer import BaseImporter

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}


class ImageImporter(BaseImporter):
    """Handles image receipt files (JPEG, PNG, WebP, etc.)."""

    @property
    def supported_extensions(self) -> List[str]:
        return sorted(_IMAGE_EXTENSIONS)

    def can_import(self, path: Path) -> bool:
        return path.suffix.lower() in _IMAGE_EXTENSIONS

    def extract(self, path: Path) -> Dict[str, Any]:
        """
        Extract data from an image receipt.
        Returns an empty skeleton; real extraction requires an OCR engine.
        """
        return {"shop": "", "purchase_date": "", "total_amount": None, "items": []}
