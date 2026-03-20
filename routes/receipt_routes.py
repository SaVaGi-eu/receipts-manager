"""
Receipt and item route handlers (RM-115).
Each function receives the ReceiptService instance and returns
(status_code: int, body: dict | str) for the caller to serialise.
"""

from typing import Any, Dict, Tuple


def handle_get_data(service) -> Tuple[int, Dict]:
    """GET /api/data — return all receipts and items."""
    return 200, service.get_all()


def handle_get_suggestions(service) -> Tuple[int, Dict]:
    """GET /api/suggestions — return autocomplete suggestions."""
    return 200, service.get_suggestions()


def handle_get_export_json(service) -> Tuple[int, Dict]:
    """GET /api/export/json — export all data as JSON."""
    return 200, service.export_json()


def handle_get_export_csv(service) -> Tuple[int, str]:
    """GET /api/export/csv — export all data as CSV string."""
    return 200, service.export_csv()


def handle_post_upload(service, body: bytes, content_type: str) -> Tuple[int, Dict]:
    """POST /api/upload — upload a receipt file and create a placeholder item."""
    try:
        payload = service.upload(body, content_type)
        return 200, payload
    except ValueError as exc:
        return 400, {"success": False, "error": str(exc)}


def handle_post_item(service, body: Dict[str, Any]) -> Tuple[int, Dict]:
    """POST /api/item — create a new item in an existing receipt group."""
    receipt_group_id = body.get("receipt_group_id")
    if not receipt_group_id:
        return 400, {"success": False, "error": "Missing receipt_group_id"}
    try:
        item = service.create_item(receipt_group_id, body)
        return 200, {"success": True, "item": item}
    except KeyError as exc:
        return 404, {"success": False, "error": str(exc)}


def handle_put_item(service, item_id: int, updates: Dict[str, Any]) -> Tuple[int, Dict]:
    """PUT /api/item/{id} — update an existing item."""
    try:
        item = service.update_item(item_id, updates)
        return 200, {"success": True, "item": item}
    except KeyError as exc:
        return 404, {"success": False, "error": str(exc)}
    except FileExistsError:
        return 400, {"success": False, "error": "Target file already exists"}


def handle_delete_item(service, item_id: int) -> Tuple[int, Dict]:
    """DELETE /api/item/{id} — delete an item (and its receipt group if last)."""
    try:
        service.delete_item(item_id)
        return 200, {"success": True}
    except KeyError as exc:
        return 404, {"success": False, "error": str(exc)}


def handle_post_import_json(service, body: Dict) -> Tuple[int, Dict]:
    """POST /api/import/json — replace all data with an imported JSON payload."""
    try:
        service.import_json(body)
        return 200, {"success": True, "message": "Data imported successfully"}
    except ValueError as exc:
        return 400, {"success": False, "error": str(exc)}


def handle_post_integrity_check(service) -> Tuple[int, Dict]:
    """POST /api/integrity/check — run a file integrity check."""
    issues = service.check_integrity()
    return 200, {"success": True, "issues": issues}
