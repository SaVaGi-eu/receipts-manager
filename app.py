#!/usr/bin/env python3
"""
Receipt & Warranty Manager (standalone, no Flask)
Integrated with config.py for dynamic path resolution
"""
import json
import shutil
import re
import threading
import time
import os
import logging
from datetime import datetime, timedelta
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
import mimetypes

# Internal imports (config and OCR)
from ocr_service import extract_receipt_data
from config import DATA_ROOT, DATABASE_DIR, STORAGE_DIR, RECEIPTS_DIR, BACKUP_DIR, DATA_FILE

# Basic configuration
PORT = 8765  # Avoid macOS AirPlay Receiver on port 5000
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Allowed CORS origins
ALLOWED_ORIGINS = {
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8765"
}

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("receipt-manager")

data_lock = threading.Lock()

# ---------- Path safety helpers ----------
def _is_within_root(root: Path, candidate: Path) -> bool:
    try:
        root_resolved = root.resolve()
        cand_resolved = candidate.resolve()
    except Exception:
        return False
    root_prefix = str(root_resolved) + os.sep
    cand_str = str(cand_resolved)
    return cand_str == str(root_resolved) or cand_str.startswith(root_prefix)

def safe_resolve_within(root: Path, rel_path: str) -> Path | None:
    """
    Resolve a user-supplied relative path against root safely.
    Returns the resolved Path if it is contained within root, otherwise None.
    """
    if not rel_path:
        return None
    # Decode percent-encoding
    rel = unquote(rel_path)
    # Reject absolute paths and obvious traversal tokens
    if rel.startswith("/") or rel.startswith("\\"):
        return None
    if ".." in Path(rel).parts:
        return None
    try:
        candidate = (root / rel).resolve(strict=False)
    except Exception:
        return None
    if not _is_within_root(root, candidate):
        return None
    return candidate

def safe_move_file(src: Path, dst_dir: Path, dst_name: str, allowed_root: Path) -> Path:
    """
    Move src -> dst_dir/dst_name safely.
    Returns the final destination Path on success, raises exceptions on failure.
    """
    if not src.exists() or not src.is_file():
        raise FileNotFoundError("Source file missing")

    # SECURITY: Validate dst_name doesn't contain path traversal sequences
    # Check before any path operations
    if ".." in dst_name or "/" in dst_name or "\\" in dst_name:
        raise ValueError("Invalid filename: contains path separators or traversal sequences")

    # Ensure destination directory exists
    dst_dir.mkdir(parents=True, exist_ok=True)

    # Construct destination path
    dst = dst_dir / dst_name

    # Resolve and validate destination is within allowed_root
    try:
        dst_resolved = dst.resolve(strict=False)
        allowed_root_resolved = allowed_root.resolve(strict=False)
        
        # SECURITY: Ensure resolved path is within allowed_root
        # This prevents path traversal attacks (e.g., ../../etc/passwd)
        if not dst_resolved.is_relative_to(allowed_root_resolved):
            raise ValueError("Path traversal detected: destination outside allowed directory")
    except ValueError:
        raise  # Re-raise our security check
    except Exception as e:
        raise ValueError(f"Invalid destination path: {e}")

    final_dst = dst_resolved

    # If final_dst exists and is not the same as src, fail to avoid overwrite
    if final_dst.exists():
        try:
            if final_dst.resolve() != src.resolve():
                raise FileExistsError("Target file already exists")
            else:
                # Same file already in place
                return final_dst
        except FileExistsError:
            raise
        except Exception:
            raise IOError("Unable to verify existing target")

    # Attempt atomic move; fallback to shutil.move if necessary
    try:
        try:
            os.replace(str(src), str(final_dst))
        except OSError:
            shutil.move(str(src), str(final_dst))
    except Exception as e:
        raise IOError(f"Failed to move file: {e}")

    # Optionally set safe permissions
    try:
        final_dst.chmod(0o640)
    except Exception:
        pass

    return final_dst

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

        # Fallback: keep only alphanumerics and clamp length to avoid abuse
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
                changed = (
                    json.dumps(new_cmp, sort_keys=True)
                    != json.dumps(existing, sort_keys=True)
                )
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
    # Final safety normalization on the full filename
    full = sanitize_full_filename(full, 200)
    base = "-".join(parts)
    full = f"{base}{ext}"
    if len(full) > 200:
        allowed = 200 - len(ext)
        base = base[:allowed]
        full = f"{base}{ext}"
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
    if item.get("project") and item.get("project") != "N/A":
        return STORAGE_DIR / sanitize_filename(item.get("project"), 50)
    return STORAGE_DIR / sanitize_filename(item.get("brand", "N/A"), 50)

def verify_file_integrity(data):
    issues = []
    for item in data.get("items", []):
        rel = item.get("receipt_relative_path")
        if rel:
            full = Path(rel)
            if not full.is_absolute():
                full = DATA_ROOT / rel
            if not full.exists():
                issues.append(
                    {
                        "id": item["id"],
                        "type": "item",
                        "receipt_group_id": item["receipt_group_id"],
                        "path": rel,
                    }
                )
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

# ---------- HTTP handler ----------
def set_cors_headers(handler):
    """
    Safely set CORS headers based on ALLOWED_ORIGINS and allow Electron (Origin: null).
    """
    origin = handler.headers.get("Origin")

    # Allow Electron (Origin: null)
    if origin is None or origin == "null":
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.send_header("Vary", "Origin")
        return

    # Allow known browser origins
    if origin in ALLOWED_ORIGINS:
        handler.send_header("Access-Control-Allow-Origin", origin)
        handler.send_header("Vary", "Origin")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # silence default logging; use logger instead
        logger.debug(format % args)

    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        csp = (
            "default-src 'self'; "
            "script-src 'self'; "
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

        # Serve static files safely
        if path.startswith("/static/"):
            rel = path[len("/static/"):]
            candidate = safe_resolve_within(STATIC_DIR, rel)
            if not candidate or not candidate.exists() or not candidate.is_file():
                self._set_headers(404, "text/plain")
                self.wfile.write(b"File not found")
                return

            # Whitelist extensions (optional)
            ALLOWED_STATIC_EXT = {".css", ".js", ".json", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp"}
            suffix = candidate.suffix.lower()
            if suffix not in ALLOWED_STATIC_EXT:
                ctype, _ = mimetypes.guess_type(str(candidate))
                ctype = ctype or "application/octet-stream"
            else:
                ctype, _ = mimetypes.guess_type(str(candidate))
                ctype = ctype or "application/octet-stream"

            # Stream file to avoid large memory usage
            self.send_response(200)
            self.send_header("Content-Type", f"{ctype}; charset=utf-8")
            set_cors_headers(self)
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            with candidate.open("rb") as f:
                while True:
                    chunk = f.read(64 * 1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
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
                writer.writerow([
                    "Item ID", "Receipt Group ID", "Brand", "Model", "Location", "Users",
                    "Project", "Shop", "Purchase Date", "Documentation", "Guarantee Duration",
                    "Guarantee Unit", "Guarantee End Date", "Receipt Filename", "Receipt Path"
                ])
                receipts_map = {r["receipt_group_id"]: r for r in data.get("receipts", [])}
                for item in data.get("items", []):
                    r = receipts_map.get(item["receipt_group_id"], {})
                    writer.writerow([
                        item["id"], item["receipt_group_id"], item.get("brand", ""),
                        item.get("model", ""), item.get("location", ""),
                        ";".join(item.get("users", [])), item.get("project", ""),
                        r.get("shop", ""), r.get("purchase_date", ""), r.get("documentation", ""),
                        item.get("guarantee_duration", 0), item.get("guarantee_unit", "days"),
                        item.get("guarantee_end_date", ""), r.get("receipt_filename", ""),
                        item.get("receipt_relative_path", "")
                    ])
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
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Disposition", f'inline; filename="{target.name}"')
                set_cors_headers(self)
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                with target.open("rb") as f:
                    while True:
                        chunk = f.read(64 * 1024)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
            except Exception as e:
                logger.exception("Error serving file")
                self._set_headers(500, "text/plain")
                self.wfile.write(f"Error: {e}".encode())
            return

        self._set_headers(404, "text/plain")
        self.wfile.write(b"Not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

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

            # Save uploaded file
            ext = Path(filename).suffix.lower() or ".bin"
            safe_base = sanitize_filename(Path(filename).stem, max_length=80)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            upload_dir = RECEIPTS_DIR / "uploads"
            upload_dir.mkdir(parents=True, exist_ok=True)
            saved_name = f"{ts}_{safe_base}{ext}"
            saved_path = upload_dir / saved_name
            saved_path.write_bytes(file_bytes)

            # path relative to DATA_ROOT
            try:
                rel_path = str(saved_path.relative_to(DATA_ROOT))
            except Exception:
                # If saved_path is not under DATA_ROOT, compute a safe relative path under DATA_ROOT
                rel_path = str(saved_path)

            # Run OCR extraction (best-effort)
            ocr_data = {"shop": "N/A", "purchase_date": "N/A", "total_amount": None, "items": []}
            try:
                ocr_result = extract_receipt_data(
                    str(saved_path),
                    engine="easyocr",
                    languages=["en", "nl", "el", "lv"]
                )
                ocr_data = {
                    "shop": ocr_result.get("shop", "N/A"),
                    "purchase_date": ocr_result.get("purchase_date", _today_ymmmdd()),
                    "total_amount": ocr_result.get("total_amount"),
                    "items": ocr_result.get("items", [])[:3],
                    "raw_text": ocr_result.get("raw_text", "")[:500]
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
                    "ocr_data": ocr_data
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
                old_path = (DATA_ROOT / old_rel_path) if old_rel_path else None
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
                    receipt["purchase_date"],
                    item.get("guarantee_duration", 0),
                    item.get("guarantee_unit", "days")
                )

                if needs_move and old_path and old_path.exists():
                    ext = old_path.suffix
                    new_name = build_single_item_filename(item, receipt, ext)
                    new_dir = get_storage_directory(item)
                    new_dir.mkdir(parents=True, exist_ok=True)
                    new_path = new_dir / new_name

                    # Normalize and validate target path to prevent path traversal
                    try:
                        resolved_new_dir = new_dir.resolve()
                        resolved_new_path = new_path.resolve()
                    except Exception:
                        self._set_headers(400)
                        msg = {"success": False, "error": "Invalid target path"}
                        self.wfile.write(json.dumps(msg).encode("utf-8"))
                        return

                    # Ensure the new path is within DATA_ROOT (complete containment check)
                    ALLOWED_STORAGE_ROOT = DATA_ROOT.resolve()
                    try:
                        if not resolved_new_path.is_relative_to(ALLOWED_STORAGE_ROOT):
                            self._set_headers(400)
                            msg = {"success": False, "error": "Invalid target path: outside allowed storage"}
                            self.wfile.write(json.dumps(msg).encode("utf-8"))
                            return
    
                        # Also verify parent directory is correct
                        if resolved_new_path.parent != resolved_new_dir:
                            self._set_headers(400)
                            msg = {"success": False, "error": "Invalid target path: directory mismatch"}
                            self.wfile.write(json.dumps(msg).encode("utf-8"))
                            return
                    except Exception as e:
                        self._set_headers(500)
                        msg = {"success": False, "error": f"Path validation failed: {e}"}
                        self.wfile.write(json.dumps(msg).encode("utf-8"))
                        return

                    # NOW it's safe to check if file exists
                    try:
                        if resolved_new_path.exists() and resolved_new_path != old_path.resolve():
                            self._set_headers(400)
                            msg = {"success": False, "error": f"Target file already exists: {new_name}"}
                            self.wfile.write(json.dumps(msg).encode("utf-8"))
                            return
                    except Exception:
                        self._set_headers(500)
                        self.wfile.write(json.dumps({"success": False, "error": "Failed to verify target"}).encode("utf-8"))
                        return

                    # Perform safe move using helper
                    ALLOWED_STORAGE_ROOT = DATA_ROOT.resolve()  # must match relative_to below
                    try:
                        final_dst = safe_move_file(old_path, new_dir, new_name, ALLOWED_STORAGE_ROOT)
                        rel = str(final_dst.relative_to(DATA_ROOT))
                        receipt["receipt_filename"] = new_name
                        receipt["receipt_relative_path"] = rel
                        item["receipt_relative_path"] = rel
                        try:
                            if old_path.parent.exists() and not any(old_path.parent.iterdir()):
                                old_path.parent.rmdir()
                        except Exception:
                            pass
                    except FileExistsError as e:
                        self._set_headers(400)
                        self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
                        return
                    except (ValueError, FileNotFoundError, IOError) as e:
                        logger.exception("Failed to move file")
                        self._set_headers(500)
                        self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
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
                        file_path = DATA_ROOT / rel
                        if file_path.exists():
                            try:
                                file_path.unlink()
                                try:
                                    if not any(file_path.parent.iterdir()):
                                        file_path.parent.rmdir()
                                except Exception:
                                    pass
                            except Exception as e:
                                logger.exception("Failed to delete file")
                                self._set_headers(500)
                                msg = {"success": False, "error": f"Failed to delete file: {e}"}
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
    logger.info(f"Starting server on port {PORT}")
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
