"""Receipt data model (RM-115)."""

from dataclasses import dataclass


@dataclass
class Receipt:
    """Represents a receipt group — one uploaded file, one or more items."""

    receipt_group_id: str
    shop: str = "N/A"
    purchase_date: str = ""
    documentation: str = "N/A"
    receipt_filename: str = ""
    receipt_relative_path: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Receipt":
        return cls(
            receipt_group_id=d["receipt_group_id"],
            shop=d.get("shop", "N/A"),
            purchase_date=d.get("purchase_date", ""),
            documentation=d.get("documentation", "N/A"),
            receipt_filename=d.get("receipt_filename", ""),
            receipt_relative_path=d.get("receipt_relative_path", ""),
        )

    def to_dict(self) -> dict:
        return {
            "receipt_group_id": self.receipt_group_id,
            "shop": self.shop,
            "purchase_date": self.purchase_date,
            "documentation": self.documentation,
            "receipt_filename": self.receipt_filename,
            "receipt_relative_path": self.receipt_relative_path,
        }
