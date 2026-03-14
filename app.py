#!/usr/bin/env python3
"""
Receipt & Warranty Manager (standalone, no Flask)
Integrated with config.py for dynamic path resolution
"""
import json
import logging
import mimetypes
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, unquote, urlparse

from config import BACKUP_DIR, DATA_FILE, DATA_ROOT, DATABASE_DIR, RECEIPTS_DIR, STORAGE_DIR

# Internal imports (config and OCR)
from ocr_service import extract_receipt_data

# Basic configuration
PORT = 8765  # Avoid macOS AirPlay Receiver on port 5000
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Allowed CORS origins
ALLOWED_ORIGINS = {"http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8765"}

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("receipt-manager")

data_lock = threading.Lock()


# ---------- Security helpers ----------
def sanitize_for_logging(text: str, max_length: int = 200) -> str:
    """
    SECURITY: Sanitize user-controlled input before logging to prevent log injection (CWE-117).
    Removes newlines, carriage returns, and other control characters.
    """
    if not text:
        return ""
    sanitized = re.sub(r"[\r\n\x00-\x1f\x7f]", "", str(text))
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    return sanitized


def sanitize_header_value(value: str) -> str:
    """
    SECURITY: Sanitize values used in HTTP headers to prevent response splitting.
    Removes CR, LF, and other control characters that could be used for header injection.
    """
    if not value:
        return ""
    # Remove \r, \n, and other control characters
    sanitized = re.sub(r"[\r\n\x00-\x1f\x7f]", "", str(value))
    # Also handle Unicode characters that could fold into newlines
    sanitized = sanitized.replace("\u0085", "").replace("\u2028", "").replace("\u2029", "")
    return sanitized


def safe_resolve_within(root: Path, rel_path: str) -> Optional[Path]:
    """
    SECURITY: Resolve a user-supplied relative path against root safely.
    Returns the resolved Path if it is contained within root, otherwise None.

    This function validates paths through multiple layers:
    1. Rejects empty paths
    2. Decodes percent-encoding
    3. Rejects absolute paths
    4. Rejects paths with .. components
    5. Validates final resolved path is within root using is_relative_to()
    """
    if not rel_path:
        return None

    # Decode percent-encoding
    rel = unquote(rel_path)

    # SECURITY: Reject absolute paths and path separators
    if rel.startswith("/") or rel.startswith("\\\\") or ".." in rel:
        return None

    # SECURITY: Reject paths with .. components by checking parts
    try:
        path_parts = Path(rel).parts
        if any(part == ".." or part == "." for part in path_parts):
            return None
    except Exception:
        return None

    # SECURITY: Resolve paths with explicit error handling
    try:
        root_resolved = root.resolve(strict=False)
    except Exception:
        return None

    try:
        # Construct candidate path
        candidate_path = root / rel
        candidate = candidate_path.resolve(strict=False)
    except Exception:
        return None

    # SECURITY: Explicit containment check that CodeQL can track
    try:
        if not candidate.is_relative_to(root_resolved):
            return None
    except Exception:
        return None

    return candidate


def validate_path_within_root(path: Path, root: Path) -> bool:
    """
    SECURITY: Explicitly validate that a path is within root.
    Returns True if path is safely contained within root, False otherwise.

    This is a helper for CodeQL to track path validation through data flow.
    """
    if path is None or root is None:
        return False

    try:
        resolved_path = path.resolve(strict=False)
    except Exception:
        return False

    try:
        resolved_root = root.resolve(strict=False)
    except Exception:
        return False

    try:
        return resolved_path.is_relative_to(resolved_root)
    except Exception:
        return False


def safe_move_file(src: Path, dst_dir: Path, dst_name: str, allowed_root: Path) -> Path:
    """
    SECURITY: Move src -> dst_dir/dst_name safely with comprehensive validation.
    Returns the final destination Path on success, raises exceptions on failure.

    Validation uses os.path.realpath + startswith (the pattern CodeQL recognises as a
    path-traversal sanitizer) so that taint flow is provably broken before any file
    operation.

    Validation steps:
    1. Verify source exists and is a file
    2. Reject dst_name containing path separators or ..
    3. Compute canonical real paths for src, dst_dir, and the final destination
    4. Verify all three are contained within allowed_root via realpath + startswith
    5. Check for existing files to prevent overwrites
    """
    if not src or not src.exists() or not src.is_file():
        raise FileNotFoundError("Source file missing")

    # SECURITY: Reject dst_name that contains path traversal sequences
    if not dst_name or ".." in dst_name or "/" in dst_name or "\\" in dst_name:
        raise ValueError("Invalid filename: contains path separators or traversal sequences")

    # SECURITY: Compute the canonical allowed root once.
    # Adding os.sep prevents a prefix like "/data" matching "/data_evil/...".
    try:
        allowed_root_real = os.path.realpath(str(allowed_root))
    except Exception:
        raise ValueError("Cannot resolve allowed root")
    allowed_root_prefix = allowed_root_real + os.sep

    # SECURITY: Validate source path is within allowed_root using realpath + startswith
    try:
        src_real = os.path.realpath(str(src))
    except Exception:
        raise ValueError("Cannot resolve source path")
    if not src_real.startswith(allowed_root_prefix):
        raise ValueError("Source path outside allowed root")

    # SECURITY: Validate destination directory is within allowed_root
    try:
        dst_dir_real = os.path.realpath(str(dst_dir))
    except Exception:
        raise ValueError("Cannot resolve destination directory")
    if not dst_dir_real.startswith(allowed_root_prefix):
        raise ValueError("Destination directory outside allowed root")

    # Ensure destination directory exists
    try:
        dst_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise IOError(f"Cannot create destination directory: {e}")

    # SECURITY: Compute the canonical final destination and validate it.
    # os.path.join is used so that CodeQL can track the data flow through
    # realpath into the startswith guard below.
    try:
        dst_real = os.path.realpath(os.path.join(dst_dir_real, dst_name))
    except Exception:
        raise ValueError("Invalid destination path construction")
    if not dst_real.startswith(allowed_root_prefix):
        raise ValueError("Path traversal detected: destination outside allowed directory")

    # If destination already exists, only allow it when src and dst are the same file
    if os.path.exists(dst_real):
        if dst_real != src_real:
            raise FileExistsError("Target file already exists")
        return Path(dst_real)

    # Attempt atomic move using the validated canonical path strings.
    # Both src_real and dst_real have passed the startswith guard above.
    try:
        try:
            os.replace(src_real, dst_real)
        except OSError:
            shutil.move(src_real, dst_real)
    except Exception as e:
        raise IOError(f"Failed to move file: {e}")

    # Optionally set safe permissions
    try:
        Path(dst_real).chmod(0o640)
    except Exception:
        pass

    return Path(dst_real)


# ---------- Utility functions ----------
def sanitize_filename(text, max_length=50):
    if not text or text == "N/A":
        return "NA"
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text)
    text = re.sub(r"[\s]+", "-", text)
    text = re.sub(r"-+", "-", text)
    text = text.strip("-")
    if len(text) > max_length:
        text = text[:max_length].rstrip("-")
    return text or "unnamed"


def sanitize_full_filename(name: str, max_length: int = 200) -> str:
    """
    Final safeguard for filenames that may include user-provided data.
    Removes path separators and leading dots, restricts characters, and truncates length.
    """
    # Remove any path separators outright
    name = name.replace("/", "").replace("\\", "")
    # Allow only a conservative set of characters
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    # Avoid hidden or relative-path-like names
    name = name.lstrip(".")
    # Enforce maximum length
    if max_length > 0 and len(name) > max_length:
        name = name[:max_length]
    return name or "file"


def format_date_for_filename(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%b-%d")
        return dt.strftime("%Y%b%d")
    except Exception:
        safe = re.sub(r"[^A-Za-z0-9]", "", str(date_str))
        return safe or "unknown"


def calculate_guarantee_end_date(purchase_date, duration, unit):
    if duration == 0:
        return "N/A"
    try:
        dt = datetime.strptime(purchase_date, "%Y-%b-%d")
        if unit == "days":
            end_dt = dt + timedelta(days=duration)
        elif unit == "months":
            month = dt.month + duration
            year = dt.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1
            if month == 12:
                last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = datetime(year, month + 1, 1) - timedelta(days=1)
            if dt.day <= last_day.day:
                end_dt = last_day.replace(day=dt.day)
            else:
                end_dt = last_day
        elif unit == "years":
            year = dt.year + duration
            month = dt.month
            day = dt.day
            try:
                end_dt = datetime(year, month, day)
            except ValueError:
                # fallback to last valid day of month
                if month == 12:
                    last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
                else:
                    last_day = datetime(year, month + 1, 1) - timedelta(days=1)
                end_dt = last_day
        else:
            return "N/A"
        return end_dt.strftime("%Y-%b-%d")
    except Exception:
        return "N/A"


def load_data():
    if not DATA_FILE.exists():
        return {"receipts": [], "items": [], "next_id": 1}
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if "next_id" not in data:
                data["next_id"] = max((i["id"] for i in data.get("items", [])), default=0) + 1
            return data
    except Exception:
        return {"receipts": [], "items": [], "next_id": 1}


def save_data(data):
    try:
        new_content = json.dumps(data, indent=2, ensure_ascii=False)
        if DATA_FILE.exists():
            try:
                existing = json.loads(DATA_FILE.read_text(encoding="utf-8"))
                existing.pop("integrity_issues", None)
                new_cmp = json.loads(new_content)
                new_cmp.pop("integrity_issues", None)
                changed = json.dumps(new_cmp, sort_keys=True) != json.dumps(existing, sort_keys=True)
            except Exception:
                changed = True
        else:
            changed = True

        if changed:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup = BACKUP_DIR / f"data_backup_{ts}.json"
            if DATA_FILE.exists():
                shutil.copy2(DATA_FILE, backup)

            backups = sorted(BACKUP_DIR.glob("data_backup_*.json"))
            if len(backups) > 20:
                for b in backups[:-20]:
                    b.unlink(missing_ok=True)

        with DATA_FILE.open("w", encoding="utf-8") as f:
            f.write(new_content)
        return True
    except Exception as e:
        logger.exception("Save error")
        return False


def generate_receipt_group_id(data):
    ids = [r["receipt_group_id"] for r in data.get("receipts", [])]
    numbers = []
    for rid in ids:
        m = re.search(r"RG-(\d+)", rid)
        if m:
            numbers.append(int(m.group(1)))
    return f"RG-{(max(numbers, default=0)+1):04d}"


def build_single_item_filename(item, receipt, ext):
    parts = [
        sanitize_filename(item.get("brand", "N/A"), 30),
        sanitize_filename(item.get("model", "N/A"), 30),
        format_date_for_filename(receipt.get("purchase_date", "unknown")),
        sanitize_filename(receipt.get("shop", "N/A"), 20),
        sanitize_filename(item.get("location", "N/A"), 20),
        "-".join(sanitize_filename(u, 15) for u in item.get("users", [])[:3]) if item.get("users") else "NoUser",
        sanitize_filename(receipt.get("documentation", "N/A"), 20),
    ]
    base = "-".join(parts)
    full = f"{base}{ext}"
    if len(full) > 200:
        allowed = 200 - len(ext)
        base = base[:allowed]
        full = f"{base}{ext}"
    # Final safety normalization on the full filename
    full = sanitize_full_filename(full, 200)
    return full


def build_multi_item_filename(receipt, ext):
    parts = [
        sanitize_filename(receipt.get("shop", "N/A"), 40),
        format_date_for_filename(receipt.get("purchase_date", "unknown")),
        sanitize_filename(receipt.get("documentation", "N/A"), 40),
        receipt.get("receipt_group_id", "RG-0000"),
    ]
    base = "-".join(parts)
    full = f"{base}{ext}"

    if len(full) > 200:
        allowed = 200 - len(ext) - len(receipt.get("receipt_group_id", "")) - 1
        p_str = "-".join(parts[:-1])[:allowed]
        base = f"{p_str}-{receipt.get('receipt_group_id', '')}"
        full = f"{base}{ext}"

    return sanitize_full_filename(full, 200)


def get_storage_directory(item):
    """
    SECURITY: Build storage directory path using sanitized components.
    Returns a Path within STORAGE_DIR based on project or brand.
    """
    # Sanitize to prevent path traversal
    if item.get("project") and item.get("project") != "N/A":
        safe_project = sanitize_filename(item.get("project"), 50)
        # SECURITY: Explicit construction to prevent path injection
        try:
            result = STORAGE_DIR / safe_project
        except Exception:
            return STORAGE_DIR / "default"
    else:
        safe_brand = sanitize_filename(item.get("brand", "N/A"), 50)
        # SECURITY: Explicit construction to prevent path injection
        try:
            result = STORAGE_DIR / safe_brand
        except Exception:
            return STORAGE_DIR / "default"

    # SECURITY: Validate result is within STORAGE_DIR
    if not validate_path_within_root(result, STORAGE_DIR):
        # Fallback to safe default
        return STORAGE_DIR / "default"

    return result


def verify_file_integrity(data):
    """
    SECURITY: Read-only integrity check of file existence.
    Paths were validated when originally saved via safe_move_file().
    """
    issues = []
    for item in data.get("items", []):
        rel = item.get("receipt_relative_path")
        if not rel:
            continue

        # SECURITY: Use safe_resolve_within for path validation
        full = safe_resolve_within(DATA_ROOT, rel)
        if not full:
            continue

        # Now safe to check existence
        try:
            if not full.exists():
                issues.append(
                    {
                        "id": item["id"],
                        "type": "item",
                        "receipt_group_id": item["receipt_group_id"],
                        "path": rel,
                    }
                )
        except Exception:
            pass

    return issues


def integrity_worker():
    while True:
        time.sleep(30)
        try:
            with data_lock:
                data = load_data()
                data["integrity_issues"] = verify_file_integrity(data)
                save_data(data)
        except Exception:
            logger.exception("Integrity worker error")


def _parse_multipart_file(body: bytes, content_type: str, field_name: str = "file"):
    if not content_type or "multipart/form-data" not in content_type:
        return None, None, None
    m = re.search(r"boundary=([^;]+)", content_type)
    if not m:
        return None, None, None
    boundary = m.group(1).strip().strip('"')
    b_boundary = ("--" + boundary).encode("utf-8")
    parts = body.split(b_boundary)
    for part in parts:
        part = part.strip()
        if not part or part == b"--":
            continue
        if b"\r\n\r\n" not in part:
            continue
        raw_headers, raw_content = part.split(b"\r\n\r\n", 1)
        raw_content = raw_content.rstrip(b"\r\n")
        header_lines = raw_headers.decode("utf-8", errors="replace").split("\r\n")
        headers = {}
        for line in header_lines:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        disp = headers.get("content-disposition", "")
        if "form-data" not in disp or f'name="{field_name}"' not in disp:
            continue
        fn_m = re.search(r'filename="([^"]+)"', disp)
        filename = fn_m.group(1) if fn_m else "upload.bin"
        part_ctype = headers.get("content-type", "application/octet-stream")
        return filename, raw_content, part_ctype
    return None, None, None


def _today_ymmmdd():
    return datetime.now().strftime("%Y-%b-%d")


def _open_file_dialog_macos():
    """
    RM-80: Open native macOS directory picker using AppleScript.
    Works on all macOS versions without tkinter dependency.
    Returns selected directory path or None if cancelled.
    """
    applescript = """
    try
        set theFolder to choose folder with prompt "Select Data Directory"
        set posixPath to POSIX path of theFolder
        return posixPath
    on error errMsg number errNum
        if errNum is -128 then
            return "USER_CANCELLED"
        else
            return "ERROR: " & errMsg
        end if
    end try
    """

    try:
        result = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            path = result.stdout.strip()

            # Handle user cancellation
            if path == "USER_CANCELLED":
                return None

            # Handle errors
            if path.startswith("ERROR:"):
                logger.error("AppleScript error: %s", sanitize_for_logging(path))
                return None

            # Remove trailing slash if present
            path = path.rstrip("/")

            # Validate the returned path exists and is a directory
            if path and Path(path).is_dir():
                return path
            else:
                logger.error("Selected path is not a valid directory: %s", sanitize_for_logging(path))
                return None
        else:
            logger.error("AppleScript failed with code %d: %s", result.returncode, sanitize_for_logging(result.stderr))
            return None

    except subprocess.TimeoutExpired:
        logger.error("Directory dialog timed out")
        return None
    except Exception as e:
        logger.exception("Error running AppleScript directory dialog: %s", sanitize_for_logging(str(e)))
        return None


def _open_file_dialog_linux():
    """
    RM-80: Open native Linux directory picker using zenity or kdialog.
    Fallback chain: zenity -> kdialog -> tkinter subprocess
    Returns selected directory path or None if cancelled.
    """
    # Try zenity first (most common)
    try:
        result = subprocess.run(
            ["zenity", "--file-selection", "--directory", "--title=Select Data Directory"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except FileNotFoundError:
        pass  # zenity not installed
    except Exception:
        pass

    # Try kdialog (KDE)
    try:
        result = subprocess.run(
            ["kdialog", "--getexistingdirectory", ".", "Select Data Directory"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except FileNotFoundError:
        pass  # kdialog not installed
    except Exception:
        pass

    # Fallback to tkinter subprocess
    return _open_file_dialog_tkinter()


def _open_file_dialog_tkinter():
    """
    RM-80: Fallback directory picker using tkinter in subprocess.
    Used when platform-specific dialogs are unavailable.
    Returns selected directory path or None if cancelled/error.
    """
    dialog_script = """
import sys
try:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    dir_path = filedialog.askdirectory(
        title="Select Data Directory"
    )

    root.destroy()

    if dir_path:
        print(dir_path)
        sys.exit(0)
    else:
        sys.exit(1)

except ImportError:
    print("ERROR: tkinter not available", file=sys.stderr)
    sys.exit(2)
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(3)
"""

    try:
        result = subprocess.run([sys.executable, "-c", dialog_script], capture_output=True, text=True, timeout=60)

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        elif result.returncode == 1:
            return None  # User cancelled
        else:
            logger.error("tkinter dialog error: %s", sanitize_for_logging(result.stderr))
            return None

    except subprocess.TimeoutExpired:
        logger.error("Directory dialog timed out")
        return None
    except Exception as e:
        logger.exception("Error running tkinter dialog subprocess: %s", sanitize_for_logging(str(e)))
        return None


def _open_file_dialog():
    """
    RM-80: Cross-platform directory picker.
    Automatically selects the best method for the current platform.
    Returns selected directory path or None if cancelled.
    """
    system = platform.system()

    if system == "Darwin":
        # macOS - use AppleScript (no tkinter dependency issues)
        return _open_file_dialog_macos()
    elif system == "Linux":
        # Linux - try zenity/kdialog, fallback to tkinter
        return _open_file_dialog_linux()
    elif system == "Windows":
        # Windows - tkinter works reliably
        return _open_file_dialog_tkinter()
    else:
        # Unknown platform - try tkinter
        logger.warning("Unknown platform: %s, trying tkinter", sanitize_for_logging(system))
        return _open_file_dialog_tkinter()


def _get_current_config():
    """
    RM-80: Get current configuration for frontend display.
    Returns dict with storage_type, data_path, and configured status.
    """
    from config import SETTINGS_FILE

    # Check for DATA_DIR environment variable first
    env_dir = os.environ.get("DATA_DIR")
    if env_dir:
        return {"storage_type": "local", "data_path": env_dir, "configured": True, "source": "environment"}

    # Check settings.json
    if SETTINGS_FILE.exists():
        try:
            settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            data_dir = settings.get("data_directory")
            if data_dir:
                return {"storage_type": "local", "data_path": data_dir, "configured": True, "source": "settings_file"}
        except Exception as e:
            logger.error("Error reading settings: %s", sanitize_for_logging(str(e)))

    # Not configured
    return {"storage_type": "none", "data_path": None, "configured": False, "source": "none"}


# ---------- HTTP handler ----------
def set_cors_headers(handler):
    """
    SECURITY: Safely set CORS headers with sanitized origin values.
    Prevents header injection via malicious Origin headers.
    """
    origin = handler.headers.get("Origin")

    # Allow Electron (Origin: null)
    if origin is None or origin == "null":
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.send_header("Vary", "Origin")
        return

    # SECURITY: Sanitize origin to prevent response splitting BEFORE checking
    origin_sanitized = sanitize_header_value(origin)

    # Allow known browser origins (check sanitized version)
    if origin_sanitized in ALLOWED_ORIGINS:
        # Use sanitized version in header
        handler.send_header("Access-Control-Allow-Origin", origin_sanitized)
        handler.send_header("Vary", "Origin")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # silence default logging; use logger instead
        logger.debug(format % args)

    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        # SECURITY: Sanitize content_type to prevent header injection BEFORE using
        content_type_safe = sanitize_header_value(content_type)
        self.send_header("Content-Type", content_type_safe)
        csp = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            f"connect-src 'self' http://127.0.0.1:{PORT} http://localhost:{PORT}; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        self.send_header("Content-Security-Policy", csp)
        self.send_header("X-Frame-Options", "DENY")
        set_cors_headers(self)
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(204)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length) if length > 0 else b""
        if not body:
            return {}
        try:
            return json.loads(body.decode("utf-8"))
        except Exception:
            return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            index_file = TEMPLATES_DIR / "index.html"
            if not index_file.exists():
                self._set_headers(500, "text/html")
                self.wfile.write(b"<h1>Error: templates/index.html not found</h1>")
                return
            html = index_file.read_bytes()
            self._set_headers(200, "text/html; charset=utf-8")
            self.wfile.write(html)
            return

        # SECURITY: Serve static files with path validation
        if path.startswith("/static/"):
            rel = path[len("/static/") :]
            candidate = safe_resolve_within(STATIC_DIR, rel)
            if not candidate or not candidate.exists() or not candidate.is_file():
                self._set_headers(404, "text/plain")
                self.wfile.write(b"File not found")
                return

            # Whitelist extensions
            ALLOWED_STATIC_EXT = {".css", ".js", ".json", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp"}
            suffix = candidate.suffix.lower()
            if suffix not in ALLOWED_STATIC_EXT:
                ctype, _ = mimetypes.guess_type(str(candidate))
                ctype = ctype or "application/octet-stream"
            else:
                ctype, _ = mimetypes.guess_type(str(candidate))
                ctype = ctype or "application/octet-stream"

            # SECURITY: Sanitize content type BEFORE using in header
            ctype_safe = sanitize_header_value(ctype)

            # Stream file to avoid large memory usage
            self.send_response(200)
            # Use sanitized content type
            content_type_header = ctype_safe + "; charset=utf-8"
            self.send_header("Content-Type", content_type_header)
            set_cors_headers(self)
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            # SECURITY: candidate validated by safe_resolve_within()
            with candidate.open("rb") as f:
                while True:
                    chunk = f.read(64 * 1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
            return

        # RM-80: Get current configuration
        if path == "/api/config":
            try:
                config = _get_current_config()
                self._set_headers(200)
                self.wfile.write(json.dumps(config).encode("utf-8"))
            except Exception as e:
                logger.exception("Error getting config")
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": "Internal configuration error"}).encode("utf-8"))
            return

        # RM-80: Directory browsing endpoint (cross-platform version)
        if path == "/api/browse/path":
            try:
                logger.info("[Browse] Opening directory dialog...")
                selected_path = _open_file_dialog()
                logger.info("[Browse] Result: %s", sanitize_for_logging(str(selected_path)))

                if selected_path:
                    # Validate path exists and is a directory
                    path_obj = Path(selected_path)
                    if path_obj.exists() and path_obj.is_dir():
                        self._set_headers(200)
                        self.wfile.write(json.dumps({"success": True, "path": selected_path}).encode("utf-8"))
                    else:
                        self._set_headers(200)
                        self.wfile.write(
                            json.dumps({"success": False, "error": "Selected path is not a valid directory"}).encode(
                                "utf-8"
                            )
                        )
                else:
                    self._set_headers(200)
                    self.wfile.write(json.dumps({"success": False, "error": "No directory selected"}).encode("utf-8"))
            except Exception as e:
                logger.exception("Error in browse endpoint")
                self._set_headers(500)
                self.wfile.write(json.dumps({"success": False, "error": "Internal server error"}).encode("utf-8"))
            return

        if path == "/api/data":
            with data_lock:
                data = load_data()
                data["integrity_issues"] = verify_file_integrity(data)
                self._set_headers(200)
                self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        if path == "/api/suggestions":
            with data_lock:
                data = load_data()
                shops = [r["shop"] for r in data.get("receipts", []) if r.get("shop")]
                brands = [i["brand"] for i in data.get("items", []) if i.get("brand")]
                models = [i["model"] for i in data.get("items", []) if i.get("model")]
                locations = [i["location"] for i in data.get("items", []) if i.get("location")]
                docs = [r["documentation"] for r in data.get("receipts", []) if r.get("documentation")]
                projects = [i["project"] for i in data.get("items", []) if i.get("project") and i["project"] != "N/A"]
                users = [u for i in data.get("items", []) for u in i.get("users", [])]
                payload = {
                    "shops": sorted(set(shops)),
                    "brands": sorted(set(brands)),
                    "models": sorted(set(models)),
                    "locations": sorted(set(locations)),
                    "documentation": sorted(set(docs)),
                    "projects": sorted(set(projects)),
                    "users": sorted(set(users)),
                }
                self._set_headers(200)
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            return

        if path == "/api/export/json":
            with data_lock:
                data = load_data()
                data.pop("integrity_issues", None)
                self._set_headers(200, "application/json; charset=utf-8")
                self.wfile.write(json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8"))
            return

        if path == "/api/export/csv":
            import csv
            from io import StringIO

            with data_lock:
                data = load_data()
                output = StringIO()
                writer = csv.writer(output)
                writer.writerow(
                    [
                        "Item ID",
                        "Receipt Group ID",
                        "Brand",
                        "Model",
                        "Location",
                        "Users",
                        "Project",
                        "Shop",
                        "Purchase Date",
                        "Documentation",
                        "Guarantee Duration",
                        "Guarantee Unit",
                        "Guarantee End Date",
                        "Receipt Filename",
                        "Receipt Path",
                    ]
                )
                receipts_map = {r["receipt_group_id"]: r for r in data.get("receipts", [])}
                for item in data.get("items", []):
                    r = receipts_map.get(item["receipt_group_id"], {})
                    writer.writerow(
                        [
                            item["id"],
                            item["receipt_group_id"],
                            item.get("brand", ""),
                            item.get("model", ""),
                            item.get("location", ""),
                            ";".join(item.get("users", [])),
                            item.get("project", ""),
                            r.get("shop", ""),
                            r.get("purchase_date", ""),
                            r.get("documentation", ""),
                            item.get("guarantee_duration", 0),
                            item.get("guarantee_unit", "days"),
                            item.get("guarantee_end_date", ""),
                            r.get("receipt_filename", ""),
                            item.get("receipt_relative_path", ""),
                        ]
                    )
                csv_data = output.getvalue()
                self._set_headers(200, "text/csv; charset=utf-8")
                self.wfile.write(csv_data.encode("utf-8"))
            return

        if path == "/api/file":
            qs_params = parse_qs(parsed.query)
            rel = qs_params.get("path", [None])[0]
            if not rel:
                self._set_headers(400, "text/plain")
                self.wfile.write(b"Missing 'path' parameter")
                return
            try:
                # SECURITY: Validate path using safe_resolve_within
                target = safe_resolve_within(DATA_ROOT, rel)
                if not target or not target.exists() or not target.is_file():
                    self._set_headers(404, "text/plain")
                    self.wfile.write(b"File not found")
                    return

                suffix = target.suffix.lower()
                file_content_types = {
                    ".pdf": "application/pdf",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".png": "image/png",
                    ".gif": "image/gif",
                    ".webp": "image/webp",
                }
                ctype = file_content_types.get(suffix, "application/octet-stream")

                # SECURITY: Triple sanitization for Content-Disposition
                # 1. Sanitize filename (remove path separators, limit length)
                safe_filename_step1 = sanitize_full_filename(target.name, 100)
                # 2. Sanitize for header injection (remove CR/LF)
                safe_filename_step2 = sanitize_header_value(safe_filename_step1)
                # 3. Sanitize content type
                ctype_safe = sanitize_header_value(ctype)

                self.send_response(200)
                self.send_header("Content-Type", ctype_safe)
                # SECURITY: Build header value with pre-sanitized components
                disposition_value = 'inline; filename="' + safe_filename_step2 + '"'
                self.send_header("Content-Disposition", disposition_value)
                set_cors_headers(self)
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                # SECURITY: target validated by safe_resolve_within()
                with target.open("rb") as f:
                    while True:
                        chunk = f.read(64 * 1024)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
            except Exception as e:
                logger.exception("Error serving file")
                self._set_headers(500, "text/plain")
                self.wfile.write(b"Internal server error")
            return

        self._set_headers(404, "text/plain")
        self.wfile.write(b"Not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # RM-80: Config update endpoint
        if path == "/api/config/update":
            try:
                updates = self._read_json()
                data_directory = updates.get("data_directory")

                if not data_directory:
                    self._set_headers(400)
                    self.wfile.write(
                        json.dumps({"success": False, "error": "Missing data_directory parameter"}).encode("utf-8")
                    )
                    return

                # Convert to Path and validate it's a directory
                dir_path = Path(data_directory)

                if not dir_path.is_dir():
                    self._set_headers(400)
                    self.wfile.write(
                        json.dumps({"success": False, "error": "Path is not a valid directory"}).encode("utf-8")
                    )
                    return

                # Import save_data_path from config
                from config import save_data_path

                # Validate and save the directory path
                if save_data_path(str(dir_path)):
                    self._set_headers(200)
                    self.wfile.write(
                        json.dumps(
                            {"success": True, "message": "Configuration updated. Please restart the application."}
                        ).encode("utf-8")
                    )
                else:
                    self._set_headers(400)
                    self.wfile.write(
                        json.dumps(
                            {
                                "success": False,
                                "error": "Failed to save configuration. Check if the path is a valid directory and writable.",
                            }
                        ).encode("utf-8")
                    )
            except Exception as e:
                logger.exception("Error updating config")
                self._set_headers(500)
                self.wfile.write(json.dumps({"success": False, "error": "Internal server error"}).encode("utf-8"))
            return

        if path == "/api/upload":
            length = int(self.headers.get("Content-Length", 0) or 0)
            max_len = 50 * 1024 * 1024
            if length == 0 or length > max_len:
                self._set_headers(400)
                self.wfile.write(b'{"success":false,"error":"Invalid or too large upload"}')
                return
            body = self.rfile.read(length)
            ctype = self.headers.get("Content-Type", "")
            filename, file_bytes, part_type = _parse_multipart_file(body, ctype, field_name="file")
            if not file_bytes:
                self._set_headers(400)
                self.wfile.write(b'{"success":false,"error":"No file field found"}')
                return

            # SECURITY: Sanitize uploaded filename and build safe path
            try:
                ext = Path(filename).suffix.lower() or ".bin"
                safe_base = sanitize_filename(Path(filename).stem, max_length=80)
            except Exception:
                ext = ".bin"
                safe_base = "upload"

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            upload_dir = RECEIPTS_DIR / "uploads"

            try:
                upload_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                self._set_headers(500)
                self.wfile.write(b'{"success":false,"error":"Cannot create upload directory"}')
                return

            saved_name = f"{ts}_{safe_base}{ext}"

            try:
                saved_path = upload_dir / saved_name
            except Exception:
                self._set_headers(400)
                self.wfile.write(b'{"success":false,"error":"Invalid filename"}')
                return

            # SECURITY: Validate path before writing
            if not validate_path_within_root(saved_path, RECEIPTS_DIR):
                self._set_headers(400)
                self.wfile.write(b'{"success":false,"error":"Invalid upload path"}')
                return

            try:
                saved_path.write_bytes(file_bytes)
            except Exception as e:
                logger.exception("Failed to save uploaded file")
                self._set_headers(500)
                self.wfile.write(json.dumps({"success": False, "error": "Failed to save uploaded file"}).encode())
                return

            # path relative to DATA_ROOT
            try:
                rel_path = str(saved_path.relative_to(DATA_ROOT))
            except Exception:
                rel_path = str(saved_path)

            # Run OCR extraction (best-effort)
            ocr_data = {"shop": "N/A", "purchase_date": "N/A", "total_amount": None, "items": []}
            try:
                ocr_result = extract_receipt_data(str(saved_path), engine="easyocr", languages=["en", "nl", "el", "lv"])
                ocr_data = {
                    "shop": ocr_result.get("shop", "N/A"),
                    "purchase_date": ocr_result.get("purchase_date", _today_ymmmdd()),
                    "total_amount": ocr_result.get("total_amount"),
                    "items": ocr_result.get("items", [])[:3],
                    "raw_text": ocr_result.get("raw_text", "")[:500],
                }
            except Exception:
                logger.exception("OCR extraction failed")

            with data_lock:
                data = load_data()
                rg_id = generate_receipt_group_id(data)
                receipt = {
                    "receipt_group_id": rg_id,
                    "shop": ocr_data["shop"],
                    "purchase_date": ocr_data["purchase_date"],
                    "documentation": "N/A",
                    "receipt_filename": saved_name,
                    "receipt_relative_path": rel_path,
                }
                data.setdefault("receipts", []).append(receipt)
                item_id = int(data.get("next_id", 1))
                item = {
                    "id": item_id,
                    "receipt_group_id": rg_id,
                    "brand": "N/A",
                    "model": "N/A",
                    "location": "N/A",
                    "users": [],
                    "project": "N/A",
                    "guarantee_duration": 0,
                    "guarantee_unit": "days",
                    "guarantee_end_date": "N/A",
                    "receipt_relative_path": rel_path,
                }
                data.setdefault("items", []).append(item)
                data["next_id"] = item_id + 1
                save_data(data)
                self._set_headers(200)
                payload = {
                    "success": True,
                    "receipt_group_id": rg_id,
                    "item_id": item_id,
                    "receipt_filename": saved_name,
                    "receipt_relative_path": rel_path,
                    "ocr_data": ocr_data,
                }
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            return

        if path == "/api/integrity/check":
            with data_lock:
                data = load_data()
                issues = verify_file_integrity(data)
                data["integrity_issues"] = issues
                save_data(data)
                self._set_headers(200)
                self.wfile.write(json.dumps({"success": True, "issues": issues}).encode("utf-8"))
            return

        if path == "/api/import/json":
            imported = self._read_json()
            if "receipts" not in imported or "items" not in imported:
                self._set_headers(400)
                self.wfile.write(b'{"success":false,"error":"Invalid JSON structure"}')
                return
            with data_lock:
                if "next_id" not in imported:
                    imported["next_id"] = max((i["id"] for i in imported.get("items", [])), default=0) + 1
                save_data(imported)
                self._set_headers(200)
                self.wfile.write(b'{"success":true,"message":"Data imported successfully"}')
            return

        self._set_headers(404)
        self.wfile.write(b'{"error":"not found"}')

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/item/"):
            try:
                item_id = int(path.rsplit("/", 1)[-1])
            except ValueError:
                self._set_headers(400)
                self.wfile.write(b'{"success":false,"error":"Invalid ID"}')
                return
            updates = self._read_json()
            with data_lock:
                data = load_data()
                item = next((i for i in data["items"] if i["id"] == item_id), None)
                if not item:
                    self._set_headers(404)
                    self.wfile.write(b'{"success":false,"error":"Item not found"}')
                    return
                receipt = next((r for r in data["receipts"] if r["receipt_group_id"] == item["receipt_group_id"]), None)
                if not receipt:
                    self._set_headers(404)
                    self.wfile.write(b'{"success":false,"error":"Receipt not found"}')
                    return
                items_in_group = [i for i in data["items"] if i["receipt_group_id"] == item["receipt_group_id"]]
                is_multi = len(items_in_group) > 1
                old_rel_path = item.get("receipt_relative_path")

                # SECURITY: Build old_path and validate using safe_resolve_within
                old_path = None
                if old_rel_path:
                    old_path = safe_resolve_within(DATA_ROOT, old_rel_path)

                needs_move = False

                def u(field, dest):
                    nonlocal needs_move
                    if field in updates:
                        dest[field] = updates[field]
                        if not is_multi and field in ["brand", "model", "location", "project"]:
                            needs_move = True

                u("brand", item)
                u("model", item)
                u("location", item)
                u("project", item)
                if "users" in updates:
                    item["users"] = updates["users"] or []
                    if not is_multi:
                        needs_move = True
                if "shop" in updates:
                    receipt["shop"] = updates["shop"]
                    if not is_multi:
                        needs_move = True
                if "purchase_date" in updates:
                    receipt["purchase_date"] = updates["purchase_date"]
                    if not is_multi:
                        needs_move = True
                if "documentation" in updates:
                    receipt["documentation"] = updates["documentation"]
                    if not is_multi:
                        needs_move = True
                if "guarantee_duration" in updates:
                    item["guarantee_duration"] = updates["guarantee_duration"]
                if "guarantee_unit" in updates:
                    item["guarantee_unit"] = updates["guarantee_unit"]

                item["guarantee_end_date"] = calculate_guarantee_end_date(
                    receipt["purchase_date"], item.get("guarantee_duration", 0), item.get("guarantee_unit", "days")
                )

                if needs_move and old_path and old_path.exists():
                    try:
                        ext = old_path.suffix
                        new_name = build_single_item_filename(item, receipt, ext)
                        new_dir = get_storage_directory(item)
                        new_dir.mkdir(parents=True, exist_ok=True)

                        # SECURITY: Use safe_move_file helper which validates paths
                        final_dst = safe_move_file(old_path, new_dir, new_name, DATA_ROOT)
                        rel = str(final_dst.relative_to(DATA_ROOT))
                        receipt["receipt_filename"] = new_name
                        receipt["receipt_relative_path"] = rel
                        item["receipt_relative_path"] = rel

                        # Clean up empty directory
                        try:
                            if old_path.parent.exists() and not any(old_path.parent.iterdir()):
                                old_path.parent.rmdir()
                        except Exception:
                            pass
                    except FileExistsError:
                        self._set_headers(400)
                        self.wfile.write(
                            json.dumps({"success": False, "error": "Target file already exists"}).encode("utf-8")
                        )
                        return
                    except (ValueError, FileNotFoundError, IOError):
                        logger.exception("Failed to move file")
                        self._set_headers(500)
                        self.wfile.write(json.dumps({"success": False, "error": "Failed to move file"}).encode("utf-8"))
                        return

                save_data(data)
                self._set_headers(200)
                self.wfile.write(json.dumps({"success": True, "item": item}).encode("utf-8"))
            return

        self._set_headers(404)
        self.wfile.write(b'{"error":"not found"}')

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/item/"):
            try:
                item_id = int(path.rsplit("/", 1)[-1])
            except ValueError:
                self._set_headers(400)
                self.wfile.write(b'{"success":false,"error":"Invalid ID"}')
                return
            with data_lock:
                data = load_data()
                item = next((i for i in data["items"] if i["id"] == item_id), None)
                if not item:
                    self._set_headers(404)
                    self.wfile.write(b'{"success":false,"error":"Item not found"}')
                    return
                rg_id = item["receipt_group_id"]
                items_in_group = [i for i in data["items"] if i["receipt_group_id"] == rg_id]
                if len(items_in_group) == 1:
                    rel = item.get("receipt_relative_path")
                    if rel:
                        # SECURITY: Validate path using safe_resolve_within before deletion
                        file_path = safe_resolve_within(DATA_ROOT, rel)
                        if file_path and file_path.exists():
                            try:
                                file_path.unlink()
                                try:
                                    if not any(file_path.parent.iterdir()):
                                        file_path.parent.rmdir()
                                except Exception as e:
                                    # Best-effort cleanup: failure to remove an empty directory is non-fatal
                                    logger.debug("Failed to remove parent directory %s: %s", file_path.parent, e)
                            except Exception as e:
                                logger.exception("Failed to delete file")
                                self._set_headers(500)
                                msg = {"success": False, "error": "Failed to delete file"}
                                self.wfile.write(json.dumps(msg).encode("utf-8"))
                                return

                # Remove item and possibly receipt
                data["items"] = [i for i in data["items"] if i["id"] != item_id]
                # If no items remain for the receipt, remove receipt
                if not any(i for i in data["items"] if i["receipt_group_id"] == rg_id):
                    data["receipts"] = [r for r in data["receipts"] if r["receipt_group_id"] != rg_id]
                save_data(data)
                self._set_headers(200)
                self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
            return

        self._set_headers(404)
        self.wfile.write(b'{"error":"not found"}')


# ---------- Server bootstrap ----------
def run_server():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    logger.info("Starting server on port %d", PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down server")
        server.server_close()


if __name__ == "__main__":
    # Ensure directories exist
    for d in (DATABASE_DIR, STORAGE_DIR, RECEIPTS_DIR, BACKUP_DIR):
        try:
            Path(d).mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    # Start integrity worker
    t = threading.Thread(target=integrity_worker, daemon=True)
    t.start()

    run_server()
