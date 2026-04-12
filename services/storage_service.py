"""
StorageService — abstracts data persistence so the storage backend can be swapped
(e.g. JSON → SQLite) without touching business logic (RM-116).
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("receipt-manager")

_EMPTY = {"receipts": [], "items": [], "next_id": 1}
_MAX_BACKUPS = 20


class StorageService:
    """Read/write data.json with automatic versioned backups."""

    def __init__(self, data_file: Path, backup_dir: Path):
        self._data_file = Path(data_file)
        self._backup_dir = Path(backup_dir)

    def load(self) -> dict:
        if not self._data_file.exists():
            return dict(_EMPTY)
        try:
            with self._data_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if "next_id" not in data:
                data["next_id"] = max((i["id"] for i in data.get("items", [])), default=0) + 1
            return data
        except Exception:
            logger.exception("Failed to load data file, returning empty state")
            return dict(_EMPTY)

    def save(self, data: dict) -> bool:
        try:
            new_content = json.dumps(data, indent=2, ensure_ascii=False)
            changed = True
            if self._data_file.exists():
                try:
                    existing = json.loads(self._data_file.read_text(encoding="utf-8"))
                    existing.pop("integrity_issues", None)
                    cmp = json.loads(new_content)
                    cmp.pop("integrity_issues", None)
                    changed = json.dumps(cmp, sort_keys=True) != json.dumps(existing, sort_keys=True)
                except Exception:
                    logger.debug("Could not read existing data for change-detection; treating as changed")

            if changed:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                self._backup_dir.mkdir(parents=True, exist_ok=True)
                if self._data_file.exists():
                    shutil.copy2(self._data_file, self._backup_dir / f"data_backup_{ts}.json")
                backups = sorted(self._backup_dir.glob("data_backup_*.json"))
                for b in backups[: max(0, len(backups) - _MAX_BACKUPS)]:
                    b.unlink(missing_ok=True)

            with self._data_file.open("w", encoding="utf-8") as f:
                f.write(new_content)
            return True
        except Exception:
            logger.exception("Save error")
            return False
