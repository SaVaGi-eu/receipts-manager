#!/usr/bin/env python3
"""
config.py - Centralized path management for Receipt & Warranty Manager

Handles data directory resolution for:
- macOS .app: reads chosen path from ~/Library/Application Support/Receipt Manager/settings.json
- Docker: reads from DATA_DIR environment variable (default /app/data)
- Direct run (run.sh): uses ./data relative to app.py

The Electron layer is responsible for showing the folder-picker dialog on first
launch and writing the chosen path into the settings file before starting Python.
"""

import json
import os
import sys
from pathlib import Path

# ── Constants ──────────────────────────────────────────────────────────────────
APP_NAME = "Receipt Manager"

# Where Electron stores the user-chosen data path (macOS standard location)
# This file is tiny (<200 bytes) and lives in Application Support regardless
# of where the user chose to store their actual data.
SETTINGS_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

# ── Path resolution ─────────────────────────────────────────────────────────────

def get_data_root() -> Path:
    """
    Returns the root data directory as a Path object.

    Priority order:
    1. DATA_DIR environment variable  (Docker / power users)
    2. settings.json chosen by user   (macOS .app first-launch picker)
    3. ./data next to app.py          (direct run via run.sh)
    """

    # 1. Explicit environment override (Docker, CI, power users)
    env_dir = os.environ.get("DATA_DIR")
    if env_dir:
        p = Path(env_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    # 2. Electron wrote the user-chosen path into settings.json
    if SETTINGS_FILE.exists():
        try:
            settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            chosen = settings.get("data_directory")
            if chosen:
                p = Path(chosen)
                if p.exists() or _try_create(p):
                    return p
                # Path no longer accessible - fall through so Electron can re-ask
                print(f"[Config] WARNING: saved data path not accessible: {chosen}", file=sys.stderr)
        except Exception as e:
            print(f"[Config] WARNING: could not read settings.json: {e}", file=sys.stderr)

    # 3. Fallback: ./data next to app.py (direct run / first boot before picker)
    fallback = Path(__file__).parent / "data"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _try_create(p: Path) -> bool:
    """Try to create directory, return True on success."""
    try:
        p.mkdir(parents=True, exist_ok=True)
        return True
    except Exception:
        return False


def is_data_path_configured() -> bool:
    """
    Returns True if a valid data directory has been configured.
    Used by Electron to decide whether to show the folder picker.
    """
    env_dir = os.environ.get("DATA_DIR")
    if env_dir:
        return True
    if SETTINGS_FILE.exists():
        try:
            settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            chosen = settings.get("data_directory")
            if chosen and Path(chosen).exists():
                return True
        except Exception:
            pass
    return False


def save_data_path(chosen_path: str) -> bool:
    """
    Save the user-chosen data directory to settings.json.
    Called by Electron after the folder picker, but also available
    for CLI/testing use.
    """
    try:
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        settings = {
            "data_directory": str(chosen_path),
            "app_name": APP_NAME,
            "version": 1
        }
        SETTINGS_FILE.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        return True
    except Exception as e:
        print(f"[Config] ERROR: could not save settings: {e}", file=sys.stderr)
        return False


# ── Resolved paths (imported by app.py) ────────────────────────────────────────

DATA_ROOT    = get_data_root()
DATABASE_DIR = DATA_ROOT / "database"
STORAGE_DIR  = DATA_ROOT / "storage"
RECEIPTS_DIR = STORAGE_DIR / "_Receipts"
BACKUP_DIR   = DATABASE_DIR / "backups"
DATA_FILE    = DATABASE_DIR / "data.json"

# Create all required directories
for _d in (DATA_ROOT, DATABASE_DIR, STORAGE_DIR, RECEIPTS_DIR, BACKUP_DIR):
    _d.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    print(f"Data root    : {DATA_ROOT}")
    print(f"Database dir : {DATABASE_DIR}")
    print(f"Storage dir  : {STORAGE_DIR}")
    print(f"Data file    : {DATA_FILE}")
    print(f"Configured   : {is_data_path_configured()}")
