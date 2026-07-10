#!/usr/bin/env python3
"""
Receipt & Warranty Manager (standalone, no Flask)
Integrated with config.py for dynamic path resolution
"""

import hashlib
import hmac
import json
import logging
import os
import platform
import re
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from config import BACKUP_DIR, DATA_FILE, DATA_ROOT, DATABASE_DIR, RECEIPTS_DIR, STORAGE_DIR

# Basic configuration
PORT = int(os.environ.get("PORT", "8765"))  # Avoid macOS AirPlay Receiver on port 5000
# SECURITY: bind to loopback by default so the app is not exposed to the whole
# network. Docker/power users can opt into 0.0.0.0 via the HOST env var (which
# .env.example already documents).
HOST = os.environ.get("HOST", "127.0.0.1")
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Allowed CORS origins
ALLOWED_ORIGINS = {"http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8765"}

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("receipt-manager")

# ReceiptService is initialised lazily inside run_server() once we know
# that DATA_ROOT is not None.  All handler methods access it via the
# module-level `service` variable which starts as None.
service = None

# ---------- RM-166: Auth configuration ----------
_AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "false").lower() == "true"
_AUTH_USERNAME = os.environ.get("AUTH_USERNAME", "admin")
_AUTH_PASSWORD = os.environ.get("AUTH_PASSWORD", "changeme")
_SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-not-for-production")
_SESSION_COOKIE = "rm_session"
_SESSION_TTL = 8 * 3600  # 8 hours

# SECURITY: known insecure defaults that must never be used when auth is enabled.
_DEFAULT_PASSWORD = "changeme"
_DEFAULT_SECRET_KEY = "dev-secret-not-for-production"


def _validate_auth_config() -> None:
    """SECURITY: When authentication is enabled, refuse to start with the shipped
    default password or secret key. A known secret lets anyone forge HMAC session
    cookies (CWE-798), and a known password is trivially guessable. Failing loudly
    at startup is far safer than silently running with a public secret."""
    if not _AUTH_ENABLED:
        return
    problems = []
    if _AUTH_PASSWORD == _DEFAULT_PASSWORD:
        problems.append("AUTH_PASSWORD is still the default 'changeme'")
    if _SECRET_KEY == _DEFAULT_SECRET_KEY:
        problems.append("SECRET_KEY is still the insecure default")
    if len(_SECRET_KEY) < 16:
        problems.append("SECRET_KEY is too short (use >= 16 random characters)")
    if problems:
        raise SystemExit(
            "Refusing to start: authentication is enabled but insecurely configured:\n  - "
            + "\n  - ".join(problems)
            + "\nSet strong AUTH_PASSWORD and SECRET_KEY environment variables and restart."
        )


def _make_session_token(username: str) -> str:
    expiry = int(time.time()) + _SESSION_TTL
    payload = f"{username}|{expiry}"
    sig = hmac.new(_SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    import base64

    return base64.urlsafe_b64encode(f"{payload}|{sig}".encode()).decode()


def _validate_session_token(token: str) -> bool:
    try:
        import base64

        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        parts = decoded.split("|")
        if len(parts) != 3:
            return False
        username, expiry_str, sig = parts
        if time.time() > int(expiry_str):
            return False
        payload = f"{username}|{expiry_str}"
        expected = hmac.new(_SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, expected)
    except Exception:
        return False


def _get_session_token(handler) -> str | None:
    cookie_header = handler.headers.get("Cookie", "")
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith(_SESSION_COOKIE + "="):
            return part[len(_SESSION_COOKIE) + 1 :]
    return None


def _is_authenticated(handler) -> bool:
    if not _AUTH_ENABLED:
        return True
    token = _get_session_token(handler)
    return token is not None and _validate_session_token(token)


# ---------- Security helpers ----------
def sanitize_for_logging(text: str, max_length: int = 200) -> str:
    if not text:
        return ""
    sanitized = re.sub(r"[\r\n\x00-\x1f\x7f]", "", str(text))
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    return sanitized


def sanitize_header_value(value: str) -> str:
    if not value:
        return ""
    sanitized = re.sub(r"[\r\n\x00-\x1f\x7f]", "", str(value))
    sanitized = sanitized.replace("\u0085", "").replace("\u2028", "").replace("\u2029", "")
    return sanitized


def _open_file_dialog_macos():
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
            if path == "USER_CANCELLED":
                return None
            if path.startswith("ERROR:"):
                logger.error("AppleScript error: %s", sanitize_for_logging(path))
                return None
            path = path.rstrip("/")
            if path and Path(path).is_dir():
                return path
            logger.error("Selected path is not a valid directory: %s", sanitize_for_logging(path))
            return None
        logger.error("AppleScript failed with code %d: %s", result.returncode, sanitize_for_logging(result.stderr))
        return None
    except subprocess.TimeoutExpired:
        logger.error("Directory dialog timed out")
        return None
    except Exception as e:
        logger.exception("Error running AppleScript directory dialog: %s", sanitize_for_logging(str(e)))
        return None


def _open_file_dialog_linux():
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
        pass
    except Exception as e:
        logger.debug("zenity file dialog failed: %s", e)
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
        pass
    except Exception as e:
        logger.debug("kdialog file dialog failed: %s", e)
    return _open_file_dialog_tkinter()


def _open_file_dialog_tkinter():
    dialog_script = """
import sys
try:
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    dir_path = filedialog.askdirectory(title="Select Data Directory")
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
            return None
        logger.error("tkinter dialog error: %s", sanitize_for_logging(result.stderr))
        return None
    except subprocess.TimeoutExpired:
        logger.error("Directory dialog timed out")
        return None
    except Exception as e:
        logger.exception("Error running tkinter dialog subprocess: %s", sanitize_for_logging(str(e)))
        return None


def _open_file_dialog():
    system = platform.system()
    if system == "Darwin":
        return _open_file_dialog_macos()
    elif system == "Linux":
        return _open_file_dialog_linux()
    elif system == "Windows":
        return _open_file_dialog_tkinter()
    logger.warning("Unknown platform: %s, trying tkinter", sanitize_for_logging(system))
    return _open_file_dialog_tkinter()


def _get_current_config():
    from config import SETTINGS_FILE

    env_dir = os.environ.get("DATA_DIR")
    if env_dir:
        return {"storage_type": "local", "data_path": env_dir, "configured": True, "source": "environment"}
    if SETTINGS_FILE.exists():
        try:
            settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            data_dir = settings.get("data_directory")
            if data_dir:
                return {"storage_type": "local", "data_path": data_dir, "configured": True, "source": "settings_file"}
        except Exception as e:
            logger.error("Error reading settings: %s", sanitize_for_logging(str(e)))
    return {"storage_type": "none", "data_path": None, "configured": False, "source": "none"}


# ---------- RM-166: Login page helper ----------
def _serve_login_page(handler, error: str | None = None):
    login_file = TEMPLATES_DIR / "login.html"
    if not login_file.exists():
        handler.send_response(500)
        handler.send_header("Content-Type", "text/plain")
        handler.end_headers()
        handler.wfile.write(b"Login page template not found")
        return
    html = login_file.read_text(encoding="utf-8")
    error_block = f'<div class="error">{error}</div>' if error else ""
    html = html.replace("__ERROR_BLOCK__", error_block)
    body = html.encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


# ---------- HTTP handler ----------
def set_cors_headers(handler):
    # SECURITY: Only reflect explicitly allow-listed origins. Requests with no
    # Origin header (same-origin navigations, curl) don't need CORS headers, so
    # we no longer emit a wildcard "Access-Control-Allow-Origin: *".
    handler.send_header("Vary", "Origin")
    origin = handler.headers.get("Origin")
    if origin is None or origin == "null":
        return
    origin_sanitized = sanitize_header_value(origin)
    matched_origin = next((o for o in ALLOWED_ORIGINS if o == origin_sanitized), None)
    if matched_origin is not None:
        handler.send_header("Access-Control-Allow-Origin", matched_origin)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.debug(format % args)

    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", sanitize_header_value(content_type))
        csp = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            f"connect-src 'self' http://127.0.0.1:{PORT} http://localhost:{PORT}; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        self.send_header("Content-Security-Policy", csp)
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-Content-Type-Options", "nosniff")
        set_cors_headers(self)
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

    def _redirect(self, location: str, clear_cookie: bool = False):
        self.send_response(302)
        self.send_header("Location", location)
        if clear_cookie:
            self.send_header("Set-Cookie", f"{_SESSION_COOKIE}=; Path=/; HttpOnly; Max-Age=0")
        self.end_headers()

    def _service_unavailable(self):
        """Return 503 when ReceiptService is not yet initialised (DATA_ROOT=None)."""
        self._set_headers(503)
        self.wfile.write(
            json.dumps(
                {
                    "error": "Service unavailable",
                    "detail": "Data directory not configured. Set the DATA_DIR environment variable.",
                }
            ).encode("utf-8")
        )

    def do_OPTIONS(self):
        self._set_headers(204)

    # SECURITY: cap non-upload request bodies so a huge Content-Length cannot
    # exhaust memory (CWE-400). Uploads have their own 50 MB limit below.
    _MAX_BODY = 10 * 1024 * 1024  # 10 MB

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0:
            return b""
        if length > self._MAX_BODY:
            raise ValueError("Request body too large")
        return self.rfile.read(length)

    def _read_json(self):
        body = self._read_body()
        if not body:
            return {}
        try:
            return json.loads(body.decode("utf-8"))
        except Exception:
            return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Health check (no auth, always available)
        if path == "/api/auth-status":
            self._set_headers(200)
            self.wfile.write(json.dumps({"auth_enabled": _AUTH_ENABLED}).encode("utf-8"))
            return

        if path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
            return

        # RM-166: public auth endpoints
        if path == "/login":
            _serve_login_page(self)
            return
        if path == "/logout":
            self._redirect("/login", clear_cookie=True)
            return

        if not _is_authenticated(self):
            self._redirect("/login")
            return

        if path == "/" or path == "/index.html":
            index_file = TEMPLATES_DIR / "index.html"
            if not index_file.exists():
                self._set_headers(500, "text/html")
                self.wfile.write(b"<h1>Error: templates/index.html not found</h1>")
                return
            self._set_headers(200, "text/html; charset=utf-8")
            self.wfile.write(index_file.read_bytes())
            return

        # Static files
        if path.startswith("/static/"):
            rel = path[len("/static/") :]
            static_dir_real = os.path.realpath(str(STATIC_DIR))
            static_dir_prefix = static_dir_real + os.sep
            rel_decoded = unquote(rel)
            if rel_decoded.startswith("/") or rel_decoded.startswith("\\") or ".." in rel_decoded:
                self._set_headers(404, "text/plain")
                self.wfile.write(b"File not found")
                return
            candidate_real = os.path.realpath(os.path.join(static_dir_real, rel_decoded))
            if not candidate_real.startswith(static_dir_prefix) or not os.path.isfile(candidate_real):
                self._set_headers(404, "text/plain")
                self.wfile.write(b"File not found")
                return
            suffix = os.path.splitext(candidate_real)[1].lower()
            _CTYPES = {
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
            self.send_response(200)
            self.send_header("Content-Type", _CTYPES.get(suffix, "application/octet-stream") + "; charset=utf-8")
            self.send_header("X-Content-Type-Options", "nosniff")
            set_cors_headers(self)
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            with open(candidate_real, "rb") as f:
                while chunk := f.read(64 * 1024):
                    self.wfile.write(chunk)
            return

        if path == "/api/config":
            try:
                self._set_headers(200)
                self.wfile.write(json.dumps(_get_current_config()).encode("utf-8"))
            except Exception:
                logger.exception("Error getting config")
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": "Internal configuration error"}).encode("utf-8"))
            return

        if path == "/api/browse/path":
            try:
                selected_path = _open_file_dialog()
                if selected_path and Path(selected_path).is_dir():
                    self._set_headers(200)
                    self.wfile.write(json.dumps({"success": True, "path": selected_path}).encode("utf-8"))
                else:
                    self._set_headers(200)
                    self.wfile.write(json.dumps({"success": False, "error": "No directory selected"}).encode("utf-8"))
            except Exception:
                logger.exception("Error in browse endpoint")
                self._set_headers(500)
                self.wfile.write(json.dumps({"success": False, "error": "Internal server error"}).encode("utf-8"))
            return

        if path == "/api/settings":
            if service is None:
                self._service_unavailable()
                return
            self._set_headers(200)
            self.wfile.write(json.dumps(service.get_settings()).encode("utf-8"))
            return

        if path == "/api/data":
            if service is None:
                self._service_unavailable()
                return
            self._set_headers(200)
            self.wfile.write(json.dumps(service.get_all()).encode("utf-8"))
            return

        if path == "/api/suggestions":
            if service is None:
                self._service_unavailable()
                return
            self._set_headers(200)
            self.wfile.write(json.dumps(service.get_suggestions()).encode("utf-8"))
            return

        if path == "/api/export/json":
            if service is None:
                self._service_unavailable()
                return
            self._set_headers(200, "application/json; charset=utf-8")
            self.wfile.write(json.dumps(service.export_json(), indent=2, ensure_ascii=False).encode("utf-8"))
            return

        if path == "/api/export/csv":
            if service is None:
                self._service_unavailable()
                return
            self._set_headers(200, "text/csv; charset=utf-8")
            self.wfile.write(service.export_csv().encode("utf-8"))
            return

        if path == "/api/file":
            if service is None:
                self._service_unavailable()
                return
            qs_params = parse_qs(parsed.query)
            rel = qs_params.get("path", [None])[0]
            if not rel:
                self._set_headers(400, "text/plain")
                self.wfile.write(b"Missing 'path' parameter")
                return
            try:
                data_root_real = os.path.realpath(str(DATA_ROOT))
                data_root_prefix = data_root_real + os.sep
                rel_decoded = unquote(rel)
                if rel_decoded.startswith("/") or rel_decoded.startswith("\\") or ".." in rel_decoded:
                    self._set_headers(404, "text/plain")
                    self.wfile.write(b"File not found")
                    return
                target_real = os.path.realpath(os.path.join(data_root_real, rel_decoded))
                if not target_real.startswith(data_root_prefix) or not os.path.isfile(target_real):
                    self._set_headers(404, "text/plain")
                    self.wfile.write(b"File not found")
                    return
                suffix = os.path.splitext(target_real)[1].lower()
                _FCTYPES = {
                    ".pdf": "application/pdf",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".png": "image/png",
                    ".gif": "image/gif",
                    ".webp": "image/webp",
                }
                self.send_response(200)
                self.send_header("Content-Type", _FCTYPES.get(suffix, "application/octet-stream"))
                self.send_header("Content-Disposition", "inline")
                self.send_header("X-Content-Type-Options", "nosniff")
                set_cors_headers(self)
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                with open(target_real, "rb") as f:
                    while chunk := f.read(64 * 1024):
                        self.wfile.write(chunk)
            except Exception:
                logger.exception("Error serving file")
                self._set_headers(500, "text/plain")
                self.wfile.write(b"Internal server error")
            return

        self._set_headers(404, "text/plain")
        self.wfile.write(b"Not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # RM-166: Login form (public)
        if path == "/login":
            body = self._read_body()
            form = {}
            for part in body.decode("utf-8", errors="replace").split("&"):
                if "=" in part:
                    k, v = part.split("=", 1)
                    form[unquote(k.replace("+", " "))] = unquote(v.replace("+", " "))
            username = form.get("username", "")
            password = form.get("password", "")
            if (
                _AUTH_ENABLED
                and hmac.compare_digest(username, _AUTH_USERNAME)
                and hmac.compare_digest(password, _AUTH_PASSWORD)
            ):
                token = _make_session_token(username)
                self.send_response(302)
                self.send_header("Location", "/")
                self.send_header(
                    "Set-Cookie",
                    f"{_SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={_SESSION_TTL}",
                )
                self.end_headers()
            else:
                _serve_login_page(self, error="Invalid username or password.")
            return

        if not _is_authenticated(self):
            self._set_headers(401)
            self.wfile.write(json.dumps({"error": "Unauthorized"}).encode("utf-8"))
            return

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
                from config import save_data_path

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
                        json.dumps({"success": False, "error": "Failed to save configuration."}).encode("utf-8")
                    )
            except Exception:
                logger.exception("Error updating config")
                self._set_headers(500)
                self.wfile.write(json.dumps({"success": False, "error": "Internal server error"}).encode("utf-8"))
            return

        if path == "/api/upload":
            if service is None:
                self._service_unavailable()
                return
            length = int(self.headers.get("Content-Length", 0) or 0)
            if length == 0 or length > 50 * 1024 * 1024:
                self._set_headers(400)
                self.wfile.write(b'{"success":false,"error":"Invalid or too large upload"}')
                return
            body = self.rfile.read(length)
            ctype = self.headers.get("Content-Type", "")
            try:
                self._set_headers(200)
                self.wfile.write(json.dumps(service.upload(body, ctype)).encode("utf-8"))
            except ValueError as e:
                self._set_headers(400)
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            except Exception:
                logger.exception("Upload error")
                self._set_headers(500)
                self.wfile.write(json.dumps({"success": False, "error": "Internal server error"}).encode("utf-8"))
            return

        if path == "/api/upload/document":
            if service is None:
                self._service_unavailable()
                return
            length = int(self.headers.get("Content-Length", 0) or 0)
            if length == 0 or length > 50 * 1024 * 1024:
                self._set_headers(400)
                self.wfile.write(b'{"success":false,"error":"Invalid or too large upload"}')
                return
            body = self.rfile.read(length)
            ctype = self.headers.get("Content-Type", "")
            try:
                self._set_headers(200)
                self.wfile.write(json.dumps(service.upload_document(body, ctype)).encode("utf-8"))
            except ValueError as e:
                self._set_headers(400)
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            except Exception:
                logger.exception("Document upload error")
                self._set_headers(500)
                self.wfile.write(json.dumps({"success": False, "error": "Internal server error"}).encode("utf-8"))
            return

        if path == "/api/item":
            if service is None:
                self._service_unavailable()
                return
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
            if service is None:
                self._service_unavailable()
                return
            issues = service.check_integrity()
            self._set_headers(200)
            self.wfile.write(json.dumps({"success": True, "issues": issues}).encode("utf-8"))
            return

        if path == "/api/import/json":
            if service is None:
                self._service_unavailable()
                return
            try:
                imported = self._read_json()
                service.import_json(imported)
                self._set_headers(200)
                self.wfile.write(b'{"success":true,"message":"Data imported successfully"}')
            except ValueError as e:
                self._set_headers(400)
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            except Exception:
                logger.exception("Import error")
                self._set_headers(500)
                self.wfile.write(json.dumps({"success": False, "error": "Internal server error"}).encode("utf-8"))
            return

        self._set_headers(404)
        self.wfile.write(b'{"error":"not found"}')

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if not _is_authenticated(self):
            self._set_headers(401)
            self.wfile.write(json.dumps({"error": "Unauthorized"}).encode("utf-8"))
            return

        if path == "/api/settings":
            if service is None:
                self._service_unavailable()
                return
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
            if service is None:
                self._service_unavailable()
                return
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

        if not _is_authenticated(self):
            self._set_headers(401)
            self.wfile.write(json.dumps({"error": "Unauthorized"}).encode("utf-8"))
            return

        if path.startswith("/api/item/"):
            if service is None:
                self._service_unavailable()
                return
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
    global service

    if DATA_ROOT is not None:
        from services.receipt_service import ReceiptService

        service = ReceiptService(DATA_FILE, DATA_ROOT, RECEIPTS_DIR, STORAGE_DIR, BACKUP_DIR)
        service.start_integrity_worker()
        logger.info("[App] ReceiptService initialised at %s", DATA_ROOT)
    else:
        logger.warning(
            "[App] DATA_ROOT is None — ReceiptService not initialised. "
            "Set DATA_DIR environment variable and restart."
        )

    server = ThreadingHTTPServer((HOST, PORT), Handler)
    logger.info("Starting server on %s:%d", HOST, PORT)
    if _AUTH_ENABLED:
        logger.info("Authentication ENABLED (Docker mode)")
    elif HOST not in ("127.0.0.1", "localhost", "::1"):
        logger.warning(
            "[App] Server is bound to %s with authentication DISABLED — "
            "anyone who can reach this host has full access. Set AUTH_ENABLED=true.",
            HOST,
        )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down server")
        server.server_close()


if __name__ == "__main__":
    _validate_auth_config()

    for d in filter(None, [DATABASE_DIR, STORAGE_DIR, RECEIPTS_DIR, BACKUP_DIR]):
        try:
            Path(d).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.debug("Could not create directory %s: %s", d, e)

    run_server()
