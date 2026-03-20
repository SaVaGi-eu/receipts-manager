"""Category data model (RM-115)."""

from dataclasses import dataclass


@dataclass
class Category:
    """A single distinct category label used across items."""

    name: str

    @classmethod
    def from_str(cls, name: str) -> "Category":
        return cls(name=name.strip())

    def __str__(self) -> str:
        return self.name
