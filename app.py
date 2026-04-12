#!/usr/bin/env python3
"""
Receipt & Warranty Manager (standalone, no Flask)
Integrated with config.py for dynamic path resolution
"""
import json
import logging
import os
import platform
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from config import (
    BACKUP_DIR,
    DATA_FILE,
    DATA_ROOT,
    DATABASE_DIR,
    RECEIPTS_DIR,
    SETTINGS_FILE,
    STORAGE_DIR,
    save_data_path,
)
from services.receipt_service import ReceiptService

# Basic configuration
PORT = 8765  # Avoid macOS AirPlay Receiver on port 5000
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Allowed CORS origins
ALLOWED_ORIGINS = {"http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8765"}

_STATIC_CONTENT_TYPES = {
    ".css": "text/css",
    ".js": "application/javascript",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".webp": "image/webp",
}

_FILE_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

_CSP = (
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

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("receipt-manager")

service = ReceiptService(DATA_FILE, DATA_ROOT, RECEIPTS_DIR, STORAGE_DIR, BACKUP_DIR)


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
    except Exception as e:
        logger.debug("zenity file dialog failed: %s", e)

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
    except Exception as e:
        logger.debug("kdialog file dialog failed: %s", e)

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

    # Allow known browser origins (check sanitized version), then echo back the
    # matched value from ALLOWED_ORIGINS — a compile-time constant — rather than
    # the user-provided string.  This breaks the taint flow for CodeQL's
    # py/http-response-splitting analysis: the header value is a literal from the
    # allowlist, never the raw request data.
    matched_origin = next((o for o in ALLOWED_ORIGINS if o == origin_sanitized), None)
    if matched_origin is not None:
        handler.send_header("Access-Control-Allow-Origin", matched_origin)
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
        self.send_header("Content-Security-Policy", _CSP)
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
            logger.debug("Failed to parse request body as JSON")
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

            # SECURITY: Validate using realpath + startswith — the pattern CodeQL
            # (py/path-injection) recognises as a path-traversal sanitizer.
            static_dir_real = os.path.realpath(str(STATIC_DIR))
            static_dir_prefix = static_dir_real + os.sep

            rel_decoded = unquote(rel)
            if rel_decoded.startswith("/") or rel_decoded.startswith("\\") or ".." in rel_decoded:
                self._set_headers(404, "text/plain")
                self.wfile.write(b"File not found")
                return

            # Compute canonical path; startswith guard breaks taint flow for CodeQL
            candidate_real = os.path.realpath(os.path.join(static_dir_real, rel_decoded))
            if not candidate_real.startswith(static_dir_prefix):
                self._set_headers(404, "text/plain")
                self.wfile.write(b"File not found")
                return
            if not os.path.isfile(candidate_real):
                self._set_headers(404, "text/plain")
                self.wfile.write(b"File not found")
                return

            # SECURITY: Derive content type from a predefined dict keyed on the
            # file extension.  All values are string literals, so CodeQL's
            # py/http-response-splitting analysis sees no tainted data reaching
            # the send_header sink.
            suffix = os.path.splitext(candidate_real)[1].lower()
            ctype_safe = _STATIC_CONTENT_TYPES.get(suffix, "application/octet-stream")

            # Stream file to avoid large memory usage
            self.send_response(200)
            content_type_header = ctype_safe + "; charset=utf-8"
            self.send_header("Content-Type", content_type_header)
            set_cors_headers(self)
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            # SECURITY: candidate_real validated by realpath + startswith above
            with open(candidate_real, "rb") as f:
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

        if path == "/api/settings":
            self._set_headers(200)
            self.wfile.write(json.dumps(service.get_settings()).encode("utf-8"))
            return

        if path == "/api/data":
            self._set_headers(200)
            self.wfile.write(json.dumps(service.get_all()).encode("utf-8"))
            return

        if path == "/api/suggestions":
            self._set_headers(200)
            self.wfile.write(json.dumps(service.get_suggestions()).encode("utf-8"))
            return

        if path == "/api/export/json":
            self._set_headers(200, "application/json; charset=utf-8")
            self.wfile.write(json.dumps(service.export_json(), indent=2, ensure_ascii=False).encode("utf-8"))
            return

        if path == "/api/export/csv":
            self._set_headers(200, "text/csv; charset=utf-8")
            self.wfile.write(service.export_csv().encode("utf-8"))
            return

        if path == "/api/file":
            qs_params = parse_qs(parsed.query)
            rel = qs_params.get("path", [None])[0]
            if not rel:
                self._set_headers(400, "text/plain")
                self.wfile.write(b"Missing 'path' parameter")
                return
            try:
                # SECURITY: Validate path using realpath + startswith — the pattern
                # CodeQL (py/path-injection) recognises as a path-traversal sanitizer.
                data_root_real = os.path.realpath(str(DATA_ROOT))
                data_root_prefix = data_root_real + os.sep

                # Decode percent-encoding and reject obvious traversal early
                rel_decoded = unquote(rel)
                if rel_decoded.startswith("/") or rel_decoded.startswith("\\") or ".." in rel_decoded:
                    self._set_headers(404, "text/plain")
                    self.wfile.write(b"File not found")
                    return

                # Compute canonical path; startswith guard breaks taint flow for CodeQL
                target_real = os.path.realpath(os.path.join(data_root_real, rel_decoded))
                if not target_real.startswith(data_root_prefix):
                    self._set_headers(404, "text/plain")
                    self.wfile.write(b"File not found")
                    return
                if not os.path.isfile(target_real):
                    self._set_headers(404, "text/plain")
                    self.wfile.write(b"File not found")
                    return

                suffix = os.path.splitext(target_real)[1].lower()
                ctype = _FILE_CONTENT_TYPES.get(suffix, "application/octet-stream")

                self.send_response(200)
                self.send_header("Content-Type", ctype)
                # SECURITY: Use RFC 5987 percent-encoding for the filename so that
                # no raw user-controlled bytes appear in the header value.
                # SECURITY: send "inline" without a filename to eliminate user-derived
                # data from the header entirely (CWE-113). The browser falls back to
                # the URL path for its own display name, which is already percent-encoded.
                self.send_header("Content-Disposition", "inline")
                set_cors_headers(self)
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                # SECURITY: target_real validated by realpath + startswith above
                with open(target_real, "rb") as f:
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

                if save_data_path(str(data_directory)):
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
            try:
                payload = service.upload(body, ctype)
                self._set_headers(200)
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            except ValueError as e:
                self._set_headers(400)
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            except Exception:
                logger.exception("Upload error")
                self._set_headers(500)
                self.wfile.write(json.dumps({"success": False, "error": "Internal server error"}).encode("utf-8"))
            return

        # RM-77: Upload a standalone document (e.g. ext warranty proof)
        if path == "/api/upload/document":
            length = int(self.headers.get("Content-Length", 0) or 0)
            max_len = 50 * 1024 * 1024
            if length == 0 or length > max_len:
                self._set_headers(400)
                self.wfile.write(b'{"success":false,"error":"Invalid or too large upload"}')
                return
            body = self.rfile.read(length)
            ctype = self.headers.get("Content-Type", "")
            try:
                payload = service.upload_document(body, ctype)
                self._set_headers(200)
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            except ValueError as e:
                self._set_headers(400)
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            except Exception:
                logger.exception("Document upload error")
                self._set_headers(500)
                self.wfile.write(json.dumps({"success": False, "error": "Internal server error"}).encode("utf-8"))
            return

        # RM-123 / RM-110: Create new item in existing receipt group
        if path == "/api/item":
            body = self._read_json()
            receipt_group_id = body.get("receipt_group_id")
            if not receipt_group_id:
                self._set_headers(400)
                self.wfile.write(json.dumps({"success": False, "error": "Missing receipt_group_id"}).encode("utf-8"))
                return
            try:
                item = service.create_item(receipt_group_id, body)
                self._set_headers(200)
                self.wfile.write(json.dumps({"success": True, "item": item}).encode("utf-8"))
            except KeyError as e:
                self._set_headers(404)
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            except Exception:
                logger.exception("Error creating item")
                self._set_headers(500)
                self.wfile.write(json.dumps({"success": False, "error": "Internal server error"}).encode("utf-8"))
            return

        if path == "/api/integrity/check":
            issues = service.check_integrity()
            self._set_headers(200)
            self.wfile.write(json.dumps({"success": True, "issues": issues}).encode("utf-8"))
            return

        if path == "/api/import/json":
            imported = self._read_json()
            try:
                service.import_json(imported)
                self._set_headers(200)
                self.wfile.write(b'{"success":true,"message":"Data imported successfully"}')
            except ValueError as e:
                self._set_headers(400)
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            return

        self._set_headers(404)
        self.wfile.write(b'{"error":"not found"}')

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/settings":
            updates = self._read_json()
            try:
                settings = service.update_settings(updates)
                self._set_headers(200)
                self.wfile.write(json.dumps(settings).encode("utf-8"))
            except Exception:
                logger.exception("Error updating settings")
                self._set_headers(500)
                self.wfile.write(json.dumps({"success": False, "error": "Internal server error"}).encode("utf-8"))
            return

        if path.startswith("/api/item/"):
            try:
                item_id = int(path.rsplit("/", 1)[-1])
            except ValueError:
                self._set_headers(400)
                self.wfile.write(b'{"success":false,"error":"Invalid ID"}')
                return
            updates = self._read_json()
            try:
                item = service.update_item(item_id, updates)
                self._set_headers(200)
                self.wfile.write(json.dumps({"success": True, "item": item}).encode("utf-8"))
            except KeyError as e:
                self._set_headers(404)
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            except FileExistsError:
                self._set_headers(400)
                self.wfile.write(json.dumps({"success": False, "error": "Target file already exists"}).encode("utf-8"))
            except (ValueError, FileNotFoundError, IOError):
                logger.exception("Failed to move file")
                self._set_headers(500)
                self.wfile.write(json.dumps({"success": False, "error": "Failed to move file"}).encode("utf-8"))
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
            try:
                service.delete_item(item_id)
                self._set_headers(200)
                self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
            except KeyError as e:
                self._set_headers(404)
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            except Exception:
                logger.exception("Failed to delete item")
                self._set_headers(500)
                self.wfile.write(json.dumps({"success": False, "error": "Failed to delete"}).encode("utf-8"))
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
    # Ensure directories exist (may be None if data directory is not yet configured)
    for d in (DATABASE_DIR, STORAGE_DIR, RECEIPTS_DIR, BACKUP_DIR):
        try:
            Path(d).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.debug("Could not create directory %s: %s", d, e)

    # Start integrity worker
    service.start_integrity_worker()

    run_server()
