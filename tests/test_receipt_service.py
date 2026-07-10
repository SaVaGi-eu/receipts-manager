"""Tests for the security-critical parts of services/receipt_service.py:
path-traversal guards, the upload extension allow-list, and import validation.
"""

import pytest

from services.receipt_service import ReceiptService, safe_move_file, safe_resolve_within


@pytest.fixture
def service(tmp_path):
    data_root = tmp_path / "data"
    db_dir = data_root / "database"
    storage_dir = data_root / "storage"
    receipts_dir = storage_dir / "_Receipts"
    backup_dir = db_dir / "backups"
    for d in (db_dir, storage_dir, receipts_dir, backup_dir):
        d.mkdir(parents=True, exist_ok=True)
    return ReceiptService(db_dir / "data.json", data_root, receipts_dir, storage_dir, backup_dir)


def _multipart(filename, data=b"x"):
    boundary = "----testboundary"
    body = (
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode()
        + data
        + f"\r\n--{boundary}--\r\n".encode()
    )
    return body, f"multipart/form-data; boundary={boundary}"


# ---------- safe_resolve_within / safe_move_file (path traversal) ----------


def test_safe_resolve_within_rejects_traversal(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    assert safe_resolve_within(root, "../outside.txt") is None
    assert safe_resolve_within(root, "/etc/passwd") is None
    assert safe_resolve_within(root, "a/../../b") is None
    assert safe_resolve_within(root, "") is None


def test_safe_resolve_within_accepts_valid_relative_path(tmp_path):
    root = tmp_path / "root"
    (root / "sub").mkdir(parents=True)
    (root / "sub" / "file.txt").write_text("hi")
    resolved = safe_resolve_within(root, "sub/file.txt")
    assert resolved == (root / "sub" / "file.txt").resolve()


def test_safe_move_file_rejects_traversal_in_dst_name(tmp_path):
    root = tmp_path / "root"
    src_dir = root / "src"
    src_dir.mkdir(parents=True)
    src = src_dir / "a.txt"
    src.write_text("hi")
    with pytest.raises(ValueError):
        safe_move_file(src, root / "dst", "../escape.txt", root)


def test_safe_move_file_rejects_destination_outside_root(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    src = root / "a.txt"
    src.write_text("hi")
    with pytest.raises(ValueError):
        safe_move_file(src, outside, "a.txt", root)


def test_safe_move_file_moves_within_root(tmp_path):
    root = tmp_path / "root"
    src = root / "src" / "a.txt"
    src.parent.mkdir(parents=True)
    src.write_text("hi")
    dst_dir = root / "dst"
    result = safe_move_file(src, dst_dir, "a.txt", root)
    assert result == (dst_dir / "a.txt").resolve()
    assert result.read_text() == "hi"
    assert not src.exists()


# ---------- upload() / upload_document() extension allow-list ----------


@pytest.mark.parametrize("filename", ["evil.html", "x.svg", "shell.js", "payload.exe"])
def test_upload_rejects_disallowed_extension(service, filename):
    body, ctype = _multipart(filename)
    with pytest.raises(ValueError):
        service.upload(body, ctype)


@pytest.mark.parametrize("filename", ["receipt.pdf", "photo.JPG", "scan.png"])
def test_upload_accepts_allowed_extension(service, filename):
    body, ctype = _multipart(filename)
    result = service.upload(body, ctype)
    assert result["success"] is True
    assert result["item_id"] == 1


def test_upload_document_rejects_disallowed_extension(service):
    body, ctype = _multipart("evil.html")
    with pytest.raises(ValueError):
        service.upload_document(body, ctype)


def test_upload_document_accepts_allowed_extension(service):
    body, ctype = _multipart("warranty.pdf")
    result = service.upload_document(body, ctype)
    assert result["success"] is True


def test_upload_rejects_missing_file_field(service):
    with pytest.raises(ValueError):
        service.upload(b"not multipart", "text/plain")


# ---------- import_json() validation ----------


def test_import_json_rejects_item_missing_id(service):
    with pytest.raises(ValueError):
        service.import_json({"receipts": [], "items": [{}]})


def test_import_json_rejects_non_integer_id(service):
    with pytest.raises(ValueError):
        service.import_json({"receipts": [], "items": [{"id": "<img src=x>"}]})


def test_import_json_rejects_missing_top_level_keys(service):
    with pytest.raises(ValueError):
        service.import_json({"items": []})


def test_import_json_rejects_non_list_items(service):
    with pytest.raises(ValueError):
        service.import_json({"receipts": [], "items": "not-a-list"})


def test_import_json_accepts_valid_payload(service):
    service.import_json({"receipts": [], "items": [{"id": 5}]})
    data = service.load()
    assert data["next_id"] == 6
    assert data["items"] == [{"id": 5}]


# ---------- item lifecycle ----------


def test_create_update_delete_item(service):
    body, ctype = _multipart("receipt.pdf")
    upload_result = service.upload(body, ctype)
    item_id = upload_result["item_id"]

    updated = service.update_item(item_id, {"brand": "Acme", "model": "Widget"})
    assert updated["brand"] == "Acme"
    assert updated["model"] == "Widget"

    with pytest.raises(KeyError):
        service.update_item(9999, {"brand": "Nope"})

    service.delete_item(item_id)
    assert service.load()["items"] == []

    with pytest.raises(KeyError):
        service.delete_item(item_id)


def test_create_item_in_existing_group(service):
    body, ctype = _multipart("receipt.pdf")
    upload_result = service.upload(body, ctype)
    rg_id = upload_result["receipt_group_id"]

    item = service.create_item(rg_id, {"brand": "Second", "model": "Item"})
    assert item["receipt_group_id"] == rg_id

    with pytest.raises(KeyError):
        service.create_item("RG-9999", {})


# ---------- settings ----------


def test_update_settings_ignores_unknown_keys(service):
    settings = service.update_settings({"currency": "USD", "not_a_real_setting": "x"})
    assert settings["currency"] == "USD"
    assert "not_a_real_setting" not in settings
