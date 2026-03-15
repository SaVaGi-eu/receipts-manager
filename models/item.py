"""Item data model (RM-115)."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Item:
    """A single warranted item belonging to a receipt group."""

    id: int
    receipt_group_id: str
    brand: str = "N/A"
    model: str = "N/A"
    location: str = "N/A"
    category: str = ""
    users: List[str] = field(default_factory=list)
    project: str = "N/A"
    guarantee_duration: int = 0
    guarantee_unit: str = "months"
    guarantee_end_date: str = "N/A"
    price: Optional[float] = None
    extended_warranty: Optional[Dict[str, Any]] = None
    receipt_relative_path: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Item":
        return cls(
            id=d["id"],
            receipt_group_id=d["receipt_group_id"],
            brand=d.get("brand", "N/A"),
            model=d.get("model", "N/A"),
            location=d.get("location", "N/A"),
            category=d.get("category", ""),
            users=d.get("users", []),
            project=d.get("project", "N/A"),
            guarantee_duration=int(d.get("guarantee_duration", 0) or 0),
            guarantee_unit=d.get("guarantee_unit", "months"),
            guarantee_end_date=d.get("guarantee_end_date", "N/A"),
            price=d.get("price"),
            extended_warranty=d.get("extended_warranty"),
            receipt_relative_path=d.get("receipt_relative_path", ""),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "receipt_group_id": self.receipt_group_id,
            "brand": self.brand,
            "model": self.model,
            "location": self.location,
            "category": self.category,
            "users": self.users,
            "project": self.project,
            "guarantee_duration": self.guarantee_duration,
            "guarantee_unit": self.guarantee_unit,
            "guarantee_end_date": self.guarantee_end_date,
            "price": self.price,
            "extended_warranty": self.extended_warranty,
            "receipt_relative_path": self.receipt_relative_path,
        }
