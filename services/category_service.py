"""
CategoryService — category management helpers (RM-116).
Delegates to ReceiptService for data access.
"""

from typing import List


class CategoryService:
    """Thin layer for category-related queries."""

    def __init__(self, receipt_service):
        self._svc = receipt_service

    def get_categories(self) -> List[str]:
        """Return sorted list of all distinct categories in use."""
        return self._svc.get_suggestions().get("categories", [])

    def rename_category(self, old_name: str, new_name: str) -> int:
        """Rename a category across all items. Returns count of updated items."""
        old_name = (old_name or "").strip()
        new_name = (new_name or "").strip()
        if not old_name or not new_name or old_name == new_name:
            return 0

        with self._svc._lock:
            data = self._svc.load()
            count = 0
            for item in data.get("items", []):
                if item.get("category") == old_name:
                    item["category"] = new_name
                    count += 1
            if count:
                self._svc.save(data)
        return count
