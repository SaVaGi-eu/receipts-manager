#!/usr/bin/env python3
"""
Receipt & Warranty Manager (standalone, no Flask)
Fixed static file serving + OCR integration
"""
import json
import shutil
import re
import threading
import time
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# ✨ OCR integration
from ocr_service import extract_receipt_data

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATABASE_DIR = DATA_DIR / "database"
STORAGE_DIR = BASE_DIR / "storage"
RECEIPTS_DIR = STORAGE_DIR / "_Receipts"
BACKUP_DIR = DATA_DIR / "backups"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
DATA_FILE = DATABASE_DIR / "data.json"

for d in (DATA_DIR, DATABASE_DIR, STORAGE_DIR, RECEIPTS_DIR, BACKUP_DIR):
    d.mkdir(exist_ok=True)

data_lock = threading.Lock()

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

def format_date_for_filename(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%b-%d")
        return dt.strftime("%Y%b%d")
    except Exception:
        return date_str.replace("-", "")

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
                end_dt = datetime(year, month, 28)
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
    """
    Save data to disk. A backup is created only when the meaningful content
    has actually changed (integrity_issues is excluded from the comparison
    because it is refreshed every 30 s by the background worker).
    At most 20 backups are kept; older ones are pruned automatically.
    """
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

            if changed:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup = BACKUP_DIR / f"data_backup_{ts}.json"
                shutil.copy2(DATA_FILE, backup)
                backups = sorted(BACKUP_DIR.glob("data_backup_*.json"))
                if len(backups) > 20:
                    for b in backups[:-20]:
                        b.unlink(missing_ok=True)

        with DATA_FILE.open("w", encoding="utf-8") as f:
            f.write(new_content)
        return True
    except Exception:
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
        sanitize_filename(item["brand"], 30),
        sanitize_filename(item["model"], 30),
        format_date_for_filename(receipt["purchase_date"]),
        sanitize_filename(receipt["shop"], 20),
        sanitize_filename(item["location"], 20),
        "-".join(sanitize_filename(u, 15) for u in item["users"][:3]) if item["users"] else "NoUser",
        sanitize_filename(receipt["documentation"], 20),
    ]
    base = "-".join(parts)
    full = f"{base}{ext}"
    if len(full) > 200:
        allowed = 200 - len(ext)
        base = base[:allowed]
        full = f"{base}{ext}"
    return full

def build_multi_item_filename(receipt, ext):
    parts = [
        sanitize_filename(receipt["shop"], 40),
        format_date_for_filename(receipt["purchase_date"]),
        sanitize_filename(receipt["documentation"], 40),
        receipt["receipt_group_id"],
    ]
    base = "-".join(parts)
    full = f"{base}{ext}"
    if len(full) > 200:
        allowed = 200 - len(ext) - len(receipt["receipt_group_id"]) - 1
        p_str = "-".join(parts[:-1])[:allowed]
        base = f"{p_str}-{receipt['receipt_group_id']}"
        full = f"{base}{ext}"
    return full

def get_storage_directory(item):
    if item["project"] and item["project"] != "N/A":
        return STORAGE_DIR / sanitize_filename(item["project"], 50)
    return STORAGE_DIR / sanitize_filename(item["brand"], 50)

def verify_file_integrity(data):
    issues = []
    for item in data.get("items", []):
        rel = item.get("receipt_relative_path")
        if rel:
            full = BASE_DIR / rel
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
            pass

def _parse_multipart_file(body: bytes, content_type: str, field_name: str = "file"):
    """
    Minimal multipart/form-data parser for a single file field.
    Returns: (filename, file_bytes, part_content_type) or (None, None, None)
    """
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

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(204)

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

        if path.startswith("/static/"):
            rel_path = path.replace("/static/", "", 1)
            filepath = STATIC_DIR / rel_path
            if not filepath.exists() or not filepath.is_file():
                self._set_headers(404, "text/plain")
                self.wfile.write(b"File not found")
                return
            suffix = filepath.suffix.lower()
            content_types = {
                ".css": "text/css",
                ".js": "application/javascript",
                ".json": "application/json",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".svg": "image/svg+xml",
                ".ico": "image/x-icon",
            }
            ctype = content_types.get(suffix, "text/plain")
            self._set_headers(200, f"{ctype}; charset=utf-8")
            self.wfile.write(filepath.read_bytes())
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

        # ── Serve a stored receipt / warranty file ────────────────────────────────────
        # Usage: GET /api/file?path=storage/_Receipts/uploads/somefile.pdf
        if path == "/api/file":
            qs_params = parse_qs(parsed.query)
            rel = qs_params.get("path", [None])[0]
            if not rel:
                self._set_headers(400, "text/plain")
                self.wfile.write(b"Missing 'path' parameter")
                return
            try:
                target = (BASE_DIR / rel).resolve()
                base_resolved = BASE_DIR.resolve()
                # Security: must stay inside BASE_DIR
                if not str(target).startswith(str(base_resolved) + "/") and target != base_resolved:
                    self._set_headers(403, "text/plain")
                    self.wfile.write(b"Forbidden")
                    return
                if not target.exists() or not target.is_file():
                    self._set_headers(404, "text/plain")
                    self.wfile.write(b"File not found")
                    return
                suffix = target.suffix.lower()
                file_content_types = {
                    ".pdf":  "application/pdf",
                    ".jpg":  "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".png":  "image/png",
                    ".gif":  "image/gif",
                    ".webp": "image/webp",
                }
                ctype = file_content_types.get(suffix, "application/octet-stream")
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Disposition", f'inline; filename="{target.name}"')
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(target.read_bytes())
            except Exception as e:
                self._set_headers(500, "text/plain")
                self.wfile.write(f"Error: {e}".encode())
            return

        self._set_headers(404, "text/plain")
        self.wfile.write(b"Not found")

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length) if length > 0 else b""
        if not body:
            return {}
        try:
            return json.loads(body.decode("utf-8"))
        except Exception:
            return {}

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
            upload_dir.mkdir(exist_ok=True)
            saved_name = f"{ts}_{safe_base}{ext}"
            saved_path = upload_dir / saved_name
            saved_path.write_bytes(file_bytes)
            rel_path = str(saved_path.relative_to(BASE_DIR))

            # ✨ Run OCR extraction
            ocr_data = {"shop": "N/A", "purchase_date": "N/A", "total_amount": None, "items": []}
            try:
                ocr_result = extract_receipt_data(
                    str(saved_path),
                    engine="easyocr",
                    languages=["en", "nl", "el", "lv"]  # English, Dutch, Greek, Latvian
                )
                ocr_data = {
                    "shop": ocr_result.get("shop", "N/A"),
                    "purchase_date": ocr_result.get("purchase_date", _today_ymmmdd()),
                    "total_amount": ocr_result.get("total_amount"),
                    "items": ocr_result.get("items", [])[:3],
                    "raw_text": ocr_result.get("raw_text", "")[:500]
                }
            except Exception as e:
                print(f"OCR extraction failed: {e}")

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

                old_path = None
                if item.get("receipt_relative_path"):
                    old_path = BASE_DIR / item["receipt_relative_path"]

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
                    item["guarantee_end_date"] = calculate_guarantee_end_date(
                        receipt["purchase_date"],
                        item.get("guarantee_duration", 0),
                        item.get("guarantee_unit", "days")
                    )

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
                    new_dir.mkdir(exist_ok=True)
                    new_path = new_dir / new_name

                    if new_path.exists() and new_path != old_path:
                        self._set_headers(400)
                        msg = {"success": False, "error": f"Target file already exists: {new_name}"}
                        self.wfile.write(json.dumps(msg).encode("utf-8"))
                        return

                    try:
                        if new_path != old_path:
                            shutil.move(str(old_path), str(new_path))
                        rel = str(new_path.relative_to(BASE_DIR))
                        receipt["receipt_filename"] = new_name
                        receipt["receipt_relative_path"] = rel
                        item["receipt_relative_path"] = rel
                        try:
                            old_path.parent.rmdir()
                        except Exception:
                            pass
                    except Exception as e:
                        self._set_headers(500)
                        msg = {"success": False, "error": f"Failed to move file: {e}"}
                        self.wfile.write(json.dumps(msg).encode("utf-8"))
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
                        file_path = BASE_DIR / rel
                        if file_path.exists():
                            try:
                                file_path.unlink()
                                try:
                                    file_path.parent.rmdir()
                                except Exception:
                                    pass
                            except Exception as e:
                                self._set_headers(500)
                                msg = {"success": False, "error": f"Failed to delete file: {e}"}
                                self.wfile.write(json.dumps(msg).encode("utf-8"))
                                return

                    data["receipts"] = [r for r in data["receipts"] if r["receipt_group_id"] != rg_id]

                data["items"] = [i for i in data["items"] if i["id"] != item_id]
                save_data(data)

            self._set_headers(200)
            self.wfile.write(b'{"success":true}')
            return

        self._set_headers(404)
        self.wfile.write(b'{"error":"not found"}')


def main():
    print("=" * 60)
    print("Receipt & Warranty Manager")
    print("=" * 60)
    print()

    if not (TEMPLATES_DIR / "index.html").exists():
        print("ERROR: templates/index.html not found!")
        print("Make sure you have:")
        print("  - templates/index.html")
        print("  - static/css/style.css")
        print("  - static/js/app.js")
        return

    if not (STATIC_DIR / "css" / "style.css").exists():
        print("WARNING: static/css/style.css not found!")
        print("The app will work but look unstyled.")
        print()

    print("🚀 Server on http://127.0.0.1:5000")
    print("Press Ctrl+C to stop")
    print()

    t = threading.Thread(target=integrity_worker, daemon=True)
    t.start()

    server = HTTPServer(("127.0.0.1", 5000), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()