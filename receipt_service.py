"""
ReceiptService — unified data layer for the Receipt & Warranty Manager.
All business logic extracted from app.py as part of RM-116.
"""

import csv
import json
import logging
import os
import re
import shutil
import threading
import time
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

logger = logging.getLogger("receipt-manager")


# ---------- Module-level helpers (moved from app.py) ----------


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
    except Exception as e:
        logger.debug("Could not set permissions on %s: %s", re.sub(r"[\r\n]", "", str(dst_real)), e)

    return Path(dst_real)


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


# ---------- ReceiptService ----------


class ReceiptService:
    def __init__(self, data_file, data_root, receipts_dir, storage_dir, backup_dir):
        self._data_file = Path(data_file)
        self._data_root = Path(data_root)
        self._receipts_dir = Path(receipts_dir)
        self._storage_dir = Path(storage_dir)
        self._backup_dir = Path(backup_dir)
        self._lock = threading.Lock()

    # ---------- Persistence ----------

    def load(self) -> dict:
        if not self._data_file.exists():
            return {"receipts": [], "items": [], "next_id": 1}
        try:
            with self._data_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if "next_id" not in data:
                    data["next_id"] = max((i["id"] for i in data.get("items", [])), default=0) + 1
                return data
        except Exception:
            return {"receipts": [], "items": [], "next_id": 1}

    def save(self, data: dict) -> bool:
        from datetime import datetime as _dt

        try:
            new_content = json.dumps(data, indent=2, ensure_ascii=False)
            if self._data_file.exists():
                try:
                    existing = json.loads(self._data_file.read_text(encoding="utf-8"))
                    existing.pop("integrity_issues", None)
                    new_cmp = json.loads(new_content)
                    new_cmp.pop("integrity_issues", None)
                    changed = json.dumps(new_cmp, sort_keys=True) != json.dumps(existing, sort_keys=True)
                except Exception:
                    changed = True
            else:
                changed = True

            if changed:
                ts = _dt.now().strftime("%Y%m%d_%H%M%S")
                backup = self._backup_dir / f"data_backup_{ts}.json"
                if self._data_file.exists():
                    shutil.copy2(self._data_file, backup)

                backups = sorted(self._backup_dir.glob("data_backup_*.json"))
                if len(backups) > 20:
                    for b in backups[:-20]:
                        b.unlink(missing_ok=True)

            with self._data_file.open("w", encoding="utf-8") as f:
                f.write(new_content)
            return True
        except Exception:
            logger.exception("Save error")
            return False

    # ---------- Integrity ----------

    def check_integrity(self) -> list:
        with self._lock:
            data = self.load()
            issues = self._verify_file_integrity(data)
            data["integrity_issues"] = issues
            self.save(data)
            return issues

    def _verify_file_integrity(self, data) -> list:
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
            full = safe_resolve_within(self._data_root, rel)
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
            except Exception as e:
                logger.debug("Error checking file existence for item %s: %s", item.get("id"), e)

        return issues

    def start_integrity_worker(self):
        def worker():
            while True:
                time.sleep(30)
                try:
                    with self._lock:
                        data = self.load()
                        data["integrity_issues"] = self._verify_file_integrity(data)
                        self.save(data)
                except Exception:
                    logger.exception("Integrity worker error")

        threading.Thread(target=worker, daemon=True).start()

    # ---------- Queries ----------

    def get_all(self) -> dict:
        with self._lock:
            data = self.load()
            data["integrity_issues"] = self._verify_file_integrity(data)
            return data

    def get_suggestions(self) -> dict:
        with self._lock:
            data = self.load()
        shops = [r["shop"] for r in data.get("receipts", []) if r.get("shop")]
        brands = [i["brand"] for i in data.get("items", []) if i.get("brand")]
        models = [i["model"] for i in data.get("items", []) if i.get("model")]
        locations = [i["location"] for i in data.get("items", []) if i.get("location")]
        docs = [r["documentation"] for r in data.get("receipts", []) if r.get("documentation")]
        projects = [i["project"] for i in data.get("items", []) if i.get("project") and i["project"] != "N/A"]
        users = [u for i in data.get("items", []) for u in i.get("users", [])]
        return {
            "shops": sorted(set(shops)),
            "brands": sorted(set(brands)),
            "models": sorted(set(models)),
            "locations": sorted(set(locations)),
            "documentation": sorted(set(docs)),
            "projects": sorted(set(projects)),
            "users": sorted(set(users)),
        }

    def export_json(self) -> dict:
        with self._lock:
            data = self.load()
        data.pop("integrity_issues", None)
        return data

    def export_csv(self) -> str:
        with self._lock:
            data = self.load()
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
        return output.getvalue()

    # ---------- Importing ----------

    def upload(self, body: bytes, content_type: str) -> dict:
        filename, file_bytes, _ = _parse_multipart_file(body, content_type, field_name="file")
        if not file_bytes:
            raise ValueError("No file field found")

        try:
            ext = Path(filename).suffix.lower() or ".bin"
            safe_base = sanitize_filename(Path(filename).stem, max_length=80)
        except Exception:
            ext = ".bin"
            safe_base = "upload"

        from datetime import datetime as _dt

        ts = _dt.now().strftime("%Y%m%d_%H%M%S")
        upload_dir = self._receipts_dir / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)

        saved_name = f"{ts}_{safe_base}{ext}"
        saved_path = upload_dir / saved_name

        receipts_root_real = os.path.realpath(str(self._receipts_dir))
        receipts_root_prefix = receipts_root_real + os.sep
        saved_path_real = os.path.realpath(str(saved_path))
        if not saved_path_real.startswith(receipts_root_prefix):
            raise ValueError("Invalid upload path")
        saved_path = Path(saved_path_real)

        saved_path.write_bytes(file_bytes)

        try:
            rel_path = str(saved_path.relative_to(self._data_root))
        except Exception:
            rel_path = str(saved_path)

        with self._lock:
            data = self.load()
            rg_id = self._generate_group_id(data)
            receipt = {
                "receipt_group_id": rg_id,
                "shop": "N/A",
                "purchase_date": _today_ymmmdd(),
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
            self.save(data)

        return {
            "success": True,
            "receipt_group_id": rg_id,
            "item_id": item_id,
            "receipt_filename": saved_name,
            "receipt_relative_path": rel_path,
            "ocr_data": {"shop": "", "purchase_date": "", "total_amount": None, "items": []},
        }

    def import_json(self, imported: dict) -> None:
        if "receipts" not in imported or "items" not in imported:
            raise ValueError("Invalid JSON structure: missing 'receipts' or 'items'")
        with self._lock:
            if "next_id" not in imported:
                imported["next_id"] = max((i["id"] for i in imported.get("items", [])), default=0) + 1
            self.save(imported)

    # ---------- Commands ----------

    def update_item(self, item_id: int, updates: dict) -> dict:
        with self._lock:
            data = self.load()
            item = next((i for i in data["items"] if i["id"] == item_id), None)
            if not item:
                raise KeyError("Item not found")
            receipt = next((r for r in data["receipts"] if r["receipt_group_id"] == item["receipt_group_id"]), None)
            if not receipt:
                raise KeyError("Receipt not found")

            items_in_group = [i for i in data["items"] if i["receipt_group_id"] == item["receipt_group_id"]]
            is_multi = len(items_in_group) > 1
            old_rel_path = item.get("receipt_relative_path")
            old_path = safe_resolve_within(self._data_root, old_rel_path) if old_rel_path else None
            needs_move = False

            def _u(field, dest):
                nonlocal needs_move
                if field in updates:
                    dest[field] = updates[field]
                    if not is_multi and field in ["brand", "model", "location", "project"]:
                        needs_move = True

            _u("brand", item)
            _u("model", item)
            _u("location", item)
            _u("project", item)
            if "users" in updates:
                item["users"] = updates["users"] or []
                if not is_multi:
                    needs_move = True
            for field in ["shop", "purchase_date", "documentation"]:
                if field in updates:
                    receipt[field] = updates[field]
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
                ext = old_path.suffix
                new_name = self._build_single_filename(item, receipt, ext)
                new_dir = self._get_storage_dir(item)
                new_dir.mkdir(parents=True, exist_ok=True)
                final_dst = safe_move_file(old_path, new_dir, new_name, self._data_root)
                rel = str(final_dst.relative_to(self._data_root))
                receipt["receipt_filename"] = new_name
                receipt["receipt_relative_path"] = rel
                item["receipt_relative_path"] = rel
                try:
                    if old_path.parent.exists() and not any(old_path.parent.iterdir()):
                        old_path.parent.rmdir()
                except Exception as e:
                    logger.debug("Could not remove empty directory %s: %s", old_path.parent, e)

            self.save(data)
            return item

    def delete_item(self, item_id: int) -> None:
        with self._lock:
            data = self.load()
            item = next((i for i in data["items"] if i["id"] == item_id), None)
            if not item:
                raise KeyError("Item not found")
            rg_id = item["receipt_group_id"]
            items_in_group = [i for i in data["items"] if i["receipt_group_id"] == rg_id]
            if len(items_in_group) == 1:
                rel = item.get("receipt_relative_path")
                if rel:
                    file_path = safe_resolve_within(self._data_root, rel)
                    if file_path and file_path.exists():
                        file_path.unlink()
                        try:
                            if not any(file_path.parent.iterdir()):
                                file_path.parent.rmdir()
                        except Exception as e:
                            logger.debug("Failed to remove parent directory %s: %s", file_path.parent, e)
            data["items"] = [i for i in data["items"] if i["id"] != item_id]
            if not any(i for i in data["items"] if i["receipt_group_id"] == rg_id):
                data["receipts"] = [r for r in data["receipts"] if r["receipt_group_id"] != rg_id]
            self.save(data)

    # ---------- Private helpers ----------

    def _generate_group_id(self, data: dict) -> str:
        ids = [r["receipt_group_id"] for r in data.get("receipts", [])]
        numbers = []
        for rid in ids:
            m = re.search(r"RG-(\d+)", rid)
            if m:
                numbers.append(int(m.group(1)))
        return f"RG-{(max(numbers, default=0)+1):04d}"

    def _build_single_filename(self, item, receipt, ext) -> str:
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

    def _build_multi_filename(self, receipt, ext) -> str:
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

    def _get_storage_dir(self, item) -> Path:
        """
        SECURITY: Build storage directory path using sanitized components.
        Returns a Path within self._storage_dir based on project or brand.
        """
        # Sanitize to prevent path traversal
        if item.get("project") and item.get("project") != "N/A":
            safe_project = sanitize_filename(item.get("project"), 50)
            # SECURITY: Explicit construction to prevent path injection
            try:
                result = self._storage_dir / safe_project
            except Exception:
                return self._storage_dir / "default"
        else:
            safe_brand = sanitize_filename(item.get("brand", "N/A"), 50)
            # SECURITY: Explicit construction to prevent path injection
            try:
                result = self._storage_dir / safe_brand
            except Exception:
                return self._storage_dir / "default"

        # SECURITY: Validate result is within self._storage_dir using inline pattern CodeQL recognises
        storage_root_real = os.path.realpath(str(self._storage_dir))
        storage_root_prefix = storage_root_real + os.sep
        result_real = os.path.realpath(str(result))
        if not result_real.startswith(storage_root_prefix):
            return self._storage_dir / "default"

        return Path(result_real)
