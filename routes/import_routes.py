"""
Import/export route handlers (RM-115).
Thin wrappers delegating to ReceiptService; split from receipt_routes to
keep file size manageable.
"""

from typing import Dict, Tuple


def handle_get_export_json(service) -> Tuple[int, Dict]:
    """GET /api/export/json — export all data as a JSON dict."""
    return 200, service.export_json()


def handle_get_export_csv(service) -> Tuple[int, str]:
    """GET /api/export/csv — export all data as a CSV string."""
    return 200, service.export_csv()


def handle_post_import_json(service, body: Dict) -> Tuple[int, Dict]:
    """POST /api/import/json — replace all data with the supplied JSON payload."""
    try:
        service.import_json(body)
        return 200, {"success": True, "message": "Data imported successfully"}
    except ValueError as exc:
        return 400, {"success": False, "error": str(exc)}
