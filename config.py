#!/usr/bin/env python3
"""
config.py - Centralized path management for Receipt & Warranty Manager

Handles data directory resolution for:
- macOS .app: reads chosen path from ~/Library/Application Support/Receipt Manager/settings.json
- Docker: reads from DATA_DIR environment variable (default /app/data)
- Direct run (run.sh): requires user to configure data location

The Electron layer is responsible for showing the folder-picker dialog on first
launch and writing the chosen path into the settings file before starting Python.

IMPORTANT: This module will NOT create a fallback ./data directory automatically.
If no valid data directory is found, the application should prompt the user to choose one.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

# ── Logging ───────────────────────────────────────────────────────────────────
logger = logging.getLogger("receipt-manager.config")


def _sanitize_for_log(value) -> str:
    """
    Return a log-safe string representation of value by stripping CR/LF
    to mitigate log injection via user-controlled paths or messages.
    """
    text = str(value)
    return text.replace("\r", "").replace("\n", "")


# ── Constants ──────────────────────────────────────────────────────────────────
APP_NAME = "Receipt Manager"

# Where Electron stores the user-chosen data path (macOS standard location)
# This file is tiny (<200 bytes) and lives in Application Support regardless
# of where the user chose to store their actual data.
SETTINGS_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

# ── Path resolution ─────────────────────────────────────────────────────────────


def get_data_root() -> Optional[Path]:
    """
    Returns the root data directory as a Path object, or None if not configured.

    Priority order:
    1. DATA_DIR environment variable  (Docker / power users)
    2. settings.json chosen by user   (macOS .app first-launch picker)
    3. DEVELOPMENT MODE ONLY: ./data next to app.py (only if DEV_MODE=1 env var is set)

    Returns None if no valid data directory is found, which signals that
    the application should prompt the user to choose a location.
    """

    # 1. Explicit environment override (Docker, CI, power users)
    env_dir = os.environ.get("DATA_DIR")
    if env_dir:
        p = Path(env_dir)
        # Validate that the path is accessible
        try:
            if p.exists() and p.is_dir():
                logger.info("[Config] Using DATA_DIR environment variable: %s", p)
                return p
            # Try to create if it doesn't exist
            if _try_create(p):
                logger.info("[Config] Created DATA_DIR directory: %s", p)
                return p
        except Exception as e:
            logger.warning("[Config] DATA_DIR set but path not accessible: %s - %s", env_dir, e)

    # 2. Electron wrote the user-chosen path into settings.json
    if SETTINGS_FILE.exists():
        try:
            settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            chosen = settings.get("data_directory")
            if chosen:
                p = Path(chosen)
                # First check if it exists
                try:
                    if p.exists() and p.is_dir():
                        logger.info("[Config] Using configured data directory: %s", p)
                        return p
                    # If it doesn't exist, try to create it
                    if _try_create(p):
                        logger.info("[Config] Created configured directory: %s", p)
                        return p
                    # Path no longer accessible
                    logger.error("[Config] Configured data path not accessible: %s", chosen)
                    logger.error("[Config] The directory may have been moved, deleted, or permissions changed.")
                except Exception as e:
                    logger.error("[Config] Cannot access configured path %s: %s", chosen, e)
        except json.JSONDecodeError as e:
            logger.error("[Config] settings.json is corrupted: %s", e)
            logger.error("[Config] You may need to delete %s and reconfigure.", SETTINGS_FILE)
        except Exception as e:
            logger.error("[Config] could not read settings.json: %s", e)

    # 3. DEVELOPMENT MODE ONLY: Allow ./data fallback if explicitly enabled
    if os.environ.get("DEV_MODE") == "1":
        fallback = Path(__file__).parent / "data"
        logger.info("[Config] DEV_MODE enabled, using fallback: %s", fallback)
        try:
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback
        except Exception as e:
            logger.error("[Config] Cannot create DEV_MODE fallback: %s", e)

    # No valid data directory found
    logger.warning("[Config] No data directory configured.")
    logger.warning("[Config] Checked:")
    logger.warning("[Config]   - DATA_DIR environment variable: Not set")
    logger.warning(
        "[Config]   - Settings file: %s - %s", SETTINGS_FILE, "exists" if SETTINGS_FILE.exists() else "not found"
    )
    logger.warning("[Config] Application should prompt user to choose a data location.")
    return None


def _try_create(p: Path) -> bool:
    """Try to create directory and verify write permissions, return True on success."""
    try:
        # SECURITY: Canonicalize path with realpath to prevent path injection via
        # symlinks or '..' components before any filesystem operations.
        p_real = Path(os.path.realpath(str(p)))
        p_real.mkdir(parents=True, exist_ok=True)
        # Verify we can actually write to it
        test_file = p_real / ".write_test"
        test_file.touch()
        test_file.unlink()
        return True
    except Exception as e:
        safe_p = _sanitize_for_log(p)
        logger.error("[Config] Cannot create or write to directory %s: %s", safe_p, e)
        return False


def is_data_path_configured() -> bool:
    """
    Returns True if a valid data directory has been configured.
    Used by Electron to decide whether to show the folder picker.
    """
    result = get_data_root()
    return result is not None


def save_data_path(chosen_path: str) -> bool:
    """
    Save the user-chosen data directory to settings.json.
    Called by Electron after the folder picker, but also available
    for CLI/testing use.
    """
    try:
        # SECURITY: Reject paths containing null bytes, then resolve to a
        # canonical absolute path (resolves symlinks, removes '..' components).
        # All subsequent operations use the canonical path to prevent
        # traversal attacks via symlinks or relative path components.
        if "\x00" in str(chosen_path):
            logger.error("[Config] Rejected path containing null byte")
            return False
        p_real = os.path.realpath(str(chosen_path))
        p = Path(p_real)

        if not p.exists():
            # Try to create it
            if not _try_create(p):
                logger.error("[Config] Cannot create directory: %s", _sanitize_for_log(p_real))
                return False

        if not p.is_dir():
            logger.error("[Config] Path is not a directory: %s", _sanitize_for_log(p_real))
            return False

        # Create settings directory if needed
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)

        # Save settings — store the canonical path, not the raw user input
        from datetime import datetime

        settings = {
            "data_directory": p_real,
            "app_name": APP_NAME,
            "version": 1,
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }
        SETTINGS_FILE.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("[Config] Saved data directory: %s", _sanitize_for_log(p_real))
        return True
    except Exception as e:
        logger.error("[Config] could not save settings: %s", e)
        return False


# ── Resolved paths (imported by app.py) ────────────────────────────────────────

# Try to get data root, but don't crash if it fails
DATA_ROOT = get_data_root()

if DATA_ROOT:
    DATABASE_DIR = DATA_ROOT / "database"
    STORAGE_DIR = DATA_ROOT / "storage"
    RECEIPTS_DIR = STORAGE_DIR / "_Receipts"
    BACKUP_DIR = DATABASE_DIR / "backups"
    DATA_FILE = DATABASE_DIR / "data.json"

    # Create all required directories
    try:
        for _d in (DATA_ROOT, DATABASE_DIR, STORAGE_DIR, RECEIPTS_DIR, BACKUP_DIR):
            _d.mkdir(parents=True, exist_ok=True)
        logger.info("[Config] Data directory initialized: %s", DATA_ROOT)
    except Exception as e:
        logger.error("[Config] Could not create directory structure: %s", e)
        # Set to None so app knows there's a problem
        DATA_ROOT = None
        DATABASE_DIR = None
        STORAGE_DIR = None
        RECEIPTS_DIR = None
        BACKUP_DIR = None
        DATA_FILE = None
else:
    # Data directory not configured - set to None
    # The application (Electron) should handle this by showing a folder picker
    logger.warning("[Config] Data directory not configured - application should prompt user")
    DATABASE_DIR = None
    STORAGE_DIR = None
    RECEIPTS_DIR = None
    BACKUP_DIR = None
    DATA_FILE = None


if __name__ == "__main__":
    print("=" * 60)
    print("Receipt Manager - Configuration Check")
    print("=" * 60)
    print(f"Settings file    : {SETTINGS_FILE}")
    print(f"Settings exists  : {SETTINGS_FILE.exists()}")
    if SETTINGS_FILE.exists():
        try:
            settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            print(f"Configured path  : {settings.get('data_directory')}")
            print(f"Last updated     : {settings.get('updated_at', 'N/A')}")
        except Exception as e:
            print(f"Error reading    : {e}")
    print(f"\nDATA_DIR env var : {os.environ.get('DATA_DIR', 'Not set')}")
    print(f"DEV_MODE env var : {os.environ.get('DEV_MODE', 'Not set')}")
    print(f"\nConfigured       : {is_data_path_configured()}")
    print()
    if DATA_ROOT:
        print(f"✓ Data root      : {DATA_ROOT}")
        print(f"  Database dir   : {DATABASE_DIR}")
        print(f"  Storage dir    : {STORAGE_DIR}")
        print(f"  Data file      : {DATA_FILE}")
        print(f"  Exists         : {DATA_FILE.exists() if DATA_FILE else False}")
    else:
        print("✗ Data root      : NOT CONFIGURED")
        print("\nApplication will prompt user to choose data location.")
    print("=" * 60)
