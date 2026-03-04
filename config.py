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
    3. DEVELOPMENT MODE ONLY: ./data next to app.py (only if DEV_MODE=1 env var is set)

    If no valid data directory is found, raises RuntimeError to signal that
    the application should prompt the user to choose a location.
    """

    # 1. Explicit environment override (Docker, CI, power users)
    env_dir = os.environ.get("DATA_DIR")
    if env_dir:
        p = Path(env_dir)
        # Validate that the path is accessible
        if p.exists() and p.is_dir():
            return p
        # Try to create if it doesn't exist
        if _try_create(p):
            return p
        # If we can't access or create it, log warning and continue to next option
        print(f"[Config] WARNING: DATA_DIR environment variable set but path not accessible: {env_dir}", file=sys.stderr)

    # 2. Electron wrote the user-chosen path into settings.json
    if SETTINGS_FILE.exists():
        try:
            settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            chosen = settings.get("data_directory")
            if chosen:
                p = Path(chosen)
                # First check if it exists
                if p.exists() and p.is_dir():
                    return p
                # If it doesn't exist, try to create it
                if _try_create(p):
                    return p
                # Path no longer accessible - raise error so Electron can re-ask
                print(f"[Config] ERROR: Configured data path not accessible: {chosen}", file=sys.stderr)
                print(f"[Config] The directory may have been moved, deleted, or permissions changed.", file=sys.stderr)
                raise RuntimeError(
                    f"Configured data directory not accessible: {chosen}\n"
                    f"Please choose a new location for your data."
                )
        except json.JSONDecodeError as e:
            print(f"[Config] ERROR: settings.json is corrupted: {e}", file=sys.stderr)
            # Delete corrupted settings file so user can reconfigure
            try:
                SETTINGS_FILE.unlink()
                print(f"[Config] Deleted corrupted settings file.", file=sys.stderr)
            except Exception:
                pass
            raise RuntimeError(
                "Settings file was corrupted and has been reset.\n"
                "Please choose a location for your data."
            )
        except RuntimeError:
            # Re-raise RuntimeError from above (path not accessible)
            raise
        except Exception as e:
            print(f"[Config] ERROR: could not read settings.json: {e}", file=sys.stderr)
            raise RuntimeError(
                f"Could not read application settings: {e}\n"
                f"Please choose a location for your data."
            )

    # 3. DEVELOPMENT MODE ONLY: Allow ./data fallback if explicitly enabled
    if os.environ.get("DEV_MODE") == "1":
        fallback = Path(__file__).parent / "data"
        print(f"[Config] DEV_MODE enabled, using fallback: {fallback}", file=sys.stderr)
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback

    # No valid data directory found - signal that user needs to choose one
    print(f"[Config] ERROR: No data directory configured.", file=sys.stderr)
    print(f"[Config] Checked:", file=sys.stderr)
    print(f"[Config]   - DATA_DIR environment variable: Not set", file=sys.stderr)
    print(f"[Config]   - Settings file: {SETTINGS_FILE} - {'exists' if SETTINGS_FILE.exists() else 'not found'}", file=sys.stderr)
    raise RuntimeError(
        "No data directory configured.\n"
        "Please choose a location to store your receipts and warranty data.\n\n"
        "Tip: You can set the DATA_DIR environment variable or run in development mode with DEV_MODE=1"
    )


def _try_create(p: Path) -> bool:
    """Try to create directory, return True on success."""
    try:
        p.mkdir(parents=True, exist_ok=True)
        # Verify we can actually write to it
        test_file = p / ".write_test"
        test_file.touch()
        test_file.unlink()
        return True
    except Exception as e:
        print(f"[Config] Cannot create or write to directory {p}: {e}", file=sys.stderr)
        return False


def is_data_path_configured() -> bool:
    """
    Returns True if a valid data directory has been configured.
    Used by Electron to decide whether to show the folder picker.
    """
    # Check environment variable
    env_dir = os.environ.get("DATA_DIR")
    if env_dir:
        p = Path(env_dir)
        if p.exists() and p.is_dir():
            return True

    # Check settings file
    if SETTINGS_FILE.exists():
        try:
            settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            chosen = settings.get("data_directory")
            if chosen:
                p = Path(chosen)
                if p.exists() and p.is_dir():
                    return True
        except Exception:
            pass

    # Check dev mode fallback
    if os.environ.get("DEV_MODE") == "1":
        fallback = Path(__file__).parent / "data"
        if fallback.exists() and fallback.is_dir():
            return True

    return False


def save_data_path(chosen_path: str) -> bool:
    """
    Save the user-chosen data directory to settings.json.
    Called by Electron after the folder picker, but also available
    for CLI/testing use.
    """
    try:
        # Validate the path first
        p = Path(chosen_path)
        if not p.exists():
            # Try to create it
            if not _try_create(p):
                print(f"[Config] ERROR: Cannot create directory: {chosen_path}", file=sys.stderr)
                return False

        if not p.is_dir():
            print(f"[Config] ERROR: Path is not a directory: {chosen_path}", file=sys.stderr)
            return False

        # Create settings directory if needed
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)

        # Save settings
        from datetime import datetime
        settings = {
            "data_directory": str(chosen_path),
            "app_name": APP_NAME,
            "version": 1,
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
        SETTINGS_FILE.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[Config] Saved data directory: {chosen_path}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"[Config] ERROR: could not save settings: {e}", file=sys.stderr)
        return False


# ── Resolved paths (imported by app.py) ────────────────────────────────────────

try:
    DATA_ROOT = get_data_root()
    DATABASE_DIR = DATA_ROOT / "database"
    STORAGE_DIR = DATA_ROOT / "storage"
    RECEIPTS_DIR = STORAGE_DIR / "_Receipts"
    BACKUP_DIR = DATABASE_DIR / "backups"
    DATA_FILE = DATABASE_DIR / "data.json"

    # Create all required directories
    for _d in (DATA_ROOT, DATABASE_DIR, STORAGE_DIR, RECEIPTS_DIR, BACKUP_DIR):
        _d.mkdir(parents=True, exist_ok=True)

    print(f"[Config] Data directory initialized: {DATA_ROOT}", file=sys.stderr)

except RuntimeError as e:
    # Data directory not configured - this is expected on first run
    # The application (Electron) should handle this by showing a folder picker
    print(f"[Config] {e}", file=sys.stderr)
    # Set placeholder values so imports don't fail
    DATA_ROOT = None
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
        except Exception as e:
            print(f"Error reading    : {e}")
    print(f"\nDATA_DIR env var : {os.environ.get('DATA_DIR', 'Not set')}")
    print(f"DEV_MODE env var : {os.environ.get('DEV_MODE', 'Not set')}")
    print(f"\nConfigured       : {is_data_path_configured()}")
    print()
    if DATA_ROOT:
        print(f"Data root        : {DATA_ROOT}")
        print(f"Database dir     : {DATABASE_DIR}")
        print(f"Storage dir      : {STORAGE_DIR}")
        print(f"Data file        : {DATA_FILE}")
    else:
        print("Data root        : NOT CONFIGURED")
        print("\nApplication will prompt user to choose data location.")
    print("=" * 60)
