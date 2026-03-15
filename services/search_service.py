"""
SearchService — full-text and filtered search across receipts (RM-116).
Operates on pre-loaded data dicts so it stays stateless and unit-testable.
"""

from typing import Dict, List, Optional


class SearchService:
    """Filter and search receipt/item rows without hitting the disk."""

    @staticmethod
    def search(
        items: List[Dict],
        receipts: List[Dict],
        query: str = "",
        project: Optional[str] = None,
        category: Optional[str] = None,
        user: Optional[str] = None,
    ) -> List[Dict]:
        """
        Return a filtered list of (item, receipt) merged rows matching the criteria.

        Args:
            items:    list of item dicts from data.json
            receipts: list of receipt dicts from data.json
            query:    free-text search string (case-insensitive substring match)
            project:  exact project filter (None = all)
            category: exact category filter (None = all)
            user:     exact user filter (None = all)
        """
        rmap = {r["receipt_group_id"]: r for r in receipts}
        results = []
        q = (query or "").strip().lower()

        for item in items:
            r = rmap.get(item.get("receipt_group_id"), {})

            if project and item.get("project") != project:
                continue
            if category and item.get("category") != category:
                continue
            if user:
                users = item.get("users", [])
                if isinstance(users, str):
                    users = [u.strip() for u in users.split(";") if u.strip()]
                if user not in users:
                    continue
            if q:
                haystack = " ".join(
                    str(v or "")
                    for v in [
                        item.get("id"),
                        item.get("receipt_group_id"),
                        item.get("brand"),
                        item.get("model"),
                        item.get("location"),
                        item.get("category"),
                        item.get("project"),
                        r.get("shop"),
                        r.get("purchase_date"),
                        r.get("documentation"),
                        item.get("guarantee_end_date"),
                        ";".join(item.get("users", [])),
                    ]
                ).lower()
                if q not in haystack:
                    continue

            merged = {
                **item,
                "shop": r.get("shop", ""),
                "purchase_date": r.get("purchase_date", ""),
                "documentation": r.get("documentation", ""),
                "receipt_filename": r.get("receipt_filename", ""),
            }
            results.append(merged)

        return results
