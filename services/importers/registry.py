"""
Importer registry — maps file extensions to the appropriate BaseImporter
subclass (RM-117).  Call get_importer() or extract() for public access.
"""

from pathlib import Path
from typing import List, Optional

from .base_importer import BaseImporter
from .email_importer import EmailImporter
from .image_importer import ImageImporter
from .pdf_importer import PdfImporter

_IMPORTERS: List[BaseImporter] = [
    PdfImporter(),
    ImageImporter(),
    EmailImporter(),
]


def get_importer(path: Path) -> Optional[BaseImporter]:
    """Return the first registered importer that can handle *path*, or None."""
    for imp in _IMPORTERS:
        if imp.can_import(path):
            return imp
    return None


def extract(path: Path) -> dict:
    """
    Convenience wrapper: find an importer for *path* and run extraction.
    Returns an empty skeleton dict if no importer is found.
    """
    imp = get_importer(path)
    if imp is None:
        return {"shop": "", "purchase_date": "", "total_amount": None, "items": []}
    return imp.extract(path)
