"""
Abstract base class for all receipt importers (RM-117).
Concrete importers live alongside this module and are registered in registry.py.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List


class BaseImporter(ABC):
    """Plugin interface for extracting structured data from a receipt file."""

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """File extensions this importer handles, e.g. ['.pdf']."""

    @abstractmethod
    def can_import(self, path: Path) -> bool:
        """Return True if this importer can handle the given file."""

    @abstractmethod
    def extract(self, path: Path) -> Dict[str, Any]:
        """
        Extract structured data from a receipt file.

        Returns a dict with zero or more of the following optional keys:
            shop (str), purchase_date (str), total_amount (float | None),
            items (list[dict])  — each item dict may contain brand, model, price.
        """
